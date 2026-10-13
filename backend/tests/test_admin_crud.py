"""admin-crud tests (slice-08): intent/template/variant CRUD + business rules."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.intent import Intent
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from app.models.training_phrase import TrainingPhrase
from app.services.jwt_service import issue_token
from tests.conftest import TestingSessionLocal


def headers_for(user_id: str, role: str):
    return {"Authorization": f"Bearer {issue_token(user_id, role, f'{user_id}@test.com')}"}


HR = headers_for("hra", "hr_admin")
IT = headers_for("ita", "it_admin")


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    yield
    limiter.requests.clear()


async def seed_dynamic_intent(role_pack="hr", name="check_leave_balance"):
    """A pre-seeded dynamic workflow: intent + template (with a {balance} var) + 2 variants."""
    async with TestingSessionLocal() as s:
        intent = Intent(role_pack=role_pack, name=name, intent_type="dynamic_workflow", needs_retrain=False)
        s.add(intent)
        s.add(TrainingPhrase(intent=intent, phrase_text="What's my leave balance?"))
        template = ResponseTemplate(
            role_pack=role_pack,
            template_key=f"{name}_response",
            base_text="You have {balance} days of leave remaining.",
            allow_rephrasing=True,
            available_variables=["balance"],
        )
        s.add(template)
        await s.flush()
        s.add(ResponseVariant(template_id=template.template_id, variant_text="You have {balance} days of leave remaining.", position=0))
        s.add(ResponseVariant(template_id=template.template_id, variant_text="Your balance is {balance} days.", position=1))
        await s.commit()
        return intent.intent_id, template.template_id


async def get_ids(template_id):
    async with TestingSessionLocal() as s:
        from sqlalchemy.future import select
        res = await s.execute(select(ResponseVariant).where(ResponseVariant.template_id == template_id).order_by(ResponseVariant.position))
        vs = res.scalars().all()
        return [v.variant_id for v in vs]


# --- Create (FAQ) -----------------------------------------------------------


@pytest.mark.asyncio
async def test_create_faq_rules_and_passthrough():
    """AC: FAQ create → static_faq, empty variables, needs_retrain; passthrough stores only the original."""
    async with _client() as client:
        res = await client.post(
            "/api/admin/intents",
            headers=HR,
            json={
                "name": "ask_wfh_policy",
                "training_phrases": ["What is the WFH policy?", "Can I work from home?"],
                "response_template": {"base_text": "You may WFH up to 3 days a week.", "allow_rephrasing": True},
            },
        )
    assert res.status_code == 201
    intent = res.json()["data"]["intent"]
    assert intent["intent_type"] == "static_faq"
    assert intent["role_pack"] == "hr"
    assert intent["needs_retrain"] is True
    assert intent["response_template"]["available_variables"] == []
    # Rephraser seam (passthrough): original is the only variant.
    variants = intent["response_template"]["variants"]
    assert len(variants) == 1
    assert variants[0]["variant_text"] == "You may WFH up to 3 days a week."


@pytest.mark.asyncio
async def test_create_duplicate_name_409():
    async with _client() as client:
        body = {
            "name": "ask_wfh_policy",
            "training_phrases": ["x"],
            "response_template": {"base_text": "b"},
        }
        first = await client.post("/api/admin/intents", headers=HR, json=body)
        assert first.status_code == 201
        dup = await client.post("/api/admin/intents", headers=HR, json=body)
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_create_missing_fields_422():
    async with _client() as client:
        no_name = await client.post(
            "/api/admin/intents", headers=HR,
            json={"training_phrases": ["x"], "response_template": {"base_text": "b"}},
        )
        no_phrases = await client.post(
            "/api/admin/intents", headers=HR,
            json={"name": "x", "training_phrases": [], "response_template": {"base_text": "b"}},
        )
    assert no_name.status_code == 422
    assert no_phrases.status_code == 422


# --- Update / rename --------------------------------------------------------


@pytest.mark.asyncio
async def test_rename_dynamic_workflow_403_but_faq_ok():
    """AC: renaming a dynamic_workflow → 403; renaming a static_faq succeeds."""
    dyn_id, _ = await seed_dynamic_intent()
    async with _client() as client:
        dyn = await client.put(f"/api/admin/intents/{dyn_id}", headers=HR, json={"name": "new_name"})
        assert dyn.status_code == 403

        faq = await client.post(
            "/api/admin/intents", headers=HR,
            json={"name": "ask_policy", "training_phrases": ["a"], "response_template": {"base_text": "b"}},
        )
        faq_id = faq.json()["data"]["intent"]["id"]
        renamed = await client.put(f"/api/admin/intents/{faq_id}", headers=HR, json={"name": "ask_policy_v2"})
    assert renamed.status_code == 200
    assert renamed.json()["data"]["intent"]["name"] == "ask_policy_v2"


@pytest.mark.asyncio
async def test_update_phrases_add_remove_sets_retrain():
    faq_id = None
    async with _client() as client:
        faq = await client.post(
            "/api/admin/intents", headers=HR,
            json={"name": "ask_x", "training_phrases": ["one", "two"], "response_template": {"base_text": "b"}},
        )
        faq_id = faq.json()["data"]["intent"]["id"]
        phrase_id = faq.json()["data"]["intent"]["training_phrases"][0]["id"]
        upd = await client.put(
            f"/api/admin/intents/{faq_id}", headers=HR,
            json={"training_phrases": {"add": ["three"], "remove": [phrase_id]}},
        )
    data = upd.json()["data"]["intent"]
    texts = {p["phrase_text"] for p in data["training_phrases"]}
    assert texts == {"two", "three"}
    assert data["needs_retrain"] is True


# --- Delete -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_faq_cascades_and_dynamic_forbidden():
    """AC: DELETE static_faq removes intent+phrases+template+variants; dynamic → 403."""
    dyn_id, _ = await seed_dynamic_intent()
    async with _client() as client:
        dyn = await client.delete(f"/api/admin/intents/{dyn_id}", headers=HR)
        assert dyn.status_code == 403

        faq = await client.post(
            "/api/admin/intents", headers=HR,
            json={"name": "ask_del", "training_phrases": ["a"], "response_template": {"base_text": "b"}},
        )
        faq_id = faq.json()["data"]["intent"]["id"]
        deleted = await client.delete(f"/api/admin/intents/{faq_id}", headers=HR)
        assert deleted.status_code == 200
        assert deleted.json()["data"]["deleted_intent_id"] == faq_id

        # Gone from the list, and its template cleaned up.
        listing = await client.get("/api/admin/intents", headers=HR)
    assert all(i["id"] != faq_id for i in listing.json()["data"]["intents"])

    async with TestingSessionLocal() as s:
        from sqlalchemy.future import select
        tpl = await s.execute(select(ResponseTemplate).where(ResponseTemplate.template_key == "ask_del_response"))
        assert tpl.scalars().first() is None
        ph = await s.execute(select(TrainingPhrase).where(TrainingPhrase.intent_id == faq_id))
        assert ph.scalars().first() is None


# --- Variants ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_variant_placeholder_validation_and_original_delete_guard():
    """AC: variant PUT dropping a base placeholder → 422; DELETE on original (pos 0) → 400."""
    _, template_id = await seed_dynamic_intent()
    v0, v1 = await get_ids(template_id)
    async with _client() as client:
        # Drops {balance} that the base template requires.
        bad = await client.put(f"/api/admin/variants/{v1}", headers=HR, json={"variant_text": "You have some days."})
        assert bad.status_code == 422

        # Keeps the placeholder → OK.
        good = await client.put(f"/api/admin/variants/{v1}", headers=HR, json={"variant_text": "Balance: {balance} days."})
        assert good.status_code == 200

        # Original (position 0) cannot be deleted.
        del0 = await client.delete(f"/api/admin/variants/{v0}", headers=HR)
        assert del0.status_code == 400

        # A non-original variant can be deleted.
        del1 = await client.delete(f"/api/admin/variants/{v1}", headers=HR)
        assert del1.status_code == 200


# --- Template PUT -----------------------------------------------------------


@pytest.mark.asyncio
async def test_template_put_regenerates_via_seam():
    _, template_id = await seed_dynamic_intent()
    async with _client() as client:
        res = await client.put(
            f"/api/admin/templates/{template_id}", headers=HR,
            json={"base_text": "You currently have {balance} leave days.", "allow_rephrasing": True},
        )
    assert res.status_code == 200
    tpl = res.json()["data"]["template"]
    assert tpl["base_text"] == "You currently have {balance} leave days."
    # Passthrough regeneration → only the (new) original variant.
    assert [v["variant_text"] for v in tpl["variants"]] == ["You currently have {balance} leave days."]


# --- Cross-pack scoping -----------------------------------------------------


@pytest.mark.asyncio
async def test_cross_pack_operations_forbidden():
    """AC: any admin op on another role pack's resource → 403."""
    dyn_id, template_id = await seed_dynamic_intent(role_pack="hr")
    v0, v1 = await get_ids(template_id)
    async with _client() as client:
        # IT admin touching HR resources.
        assert (await client.put(f"/api/admin/intents/{dyn_id}", headers=IT, json={"name": "z"})).status_code == 403
        assert (await client.delete(f"/api/admin/intents/{dyn_id}", headers=IT)).status_code == 403
        assert (await client.put(f"/api/admin/templates/{template_id}", headers=IT, json={"base_text": "x"})).status_code == 403
        assert (await client.put(f"/api/admin/variants/{v1}", headers=IT, json={"variant_text": "{balance}"})).status_code == 403
        assert (await client.delete(f"/api/admin/variants/{v1}", headers=IT)).status_code == 403
        # IT admin's own intent list excludes HR intents.
        listing = await client.get("/api/admin/intents", headers=IT)
    assert listing.json()["data"]["intents"] == []


# --- Generate Similar (stubbed) ---------------------------------------------


@pytest.mark.asyncio
async def test_generate_phrases_stub_and_no_seed_422():
    dyn_id, _ = await seed_dynamic_intent()
    async with _client() as client:
        ok = await client.post(f"/api/admin/intents/{dyn_id}/generate-phrases", headers=HR, json={"count": 8})
        assert ok.status_code == 200
        # Passthrough seam returns nothing until slice-09.
        assert ok.json()["data"]["generated_phrases"] == []

        # An intent with no phrases can't seed generation.
        empty = await client.post(
            "/api/admin/intents", headers=HR,
            json={"name": "ask_empty", "training_phrases": ["seed"], "response_template": {"base_text": "b"}},
        )
        empty_id = empty.json()["data"]["intent"]["id"]
        # Remove its only phrase, then try to generate.
        pid = empty.json()["data"]["intent"]["training_phrases"][0]["id"]
        await client.put(f"/api/admin/intents/{empty_id}", headers=HR, json={"training_phrases": {"remove": [pid]}})
        no_seed = await client.post(f"/api/admin/intents/{empty_id}/generate-phrases", headers=HR)
    assert no_seed.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_forbidden_on_crud():
    async with _client() as client:
        res = await client.get("/api/admin/intents", headers=headers_for("u", "end_user"))
    assert res.status_code == 403
