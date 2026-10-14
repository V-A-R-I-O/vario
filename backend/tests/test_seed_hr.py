import pytest
from sqlalchemy import select

from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from scripts.seed import seed_hr_data


@pytest.mark.asyncio
async def test_seed_hr_data_creates_intents_and_template(db_session):
    # AC 4: Given the seed step, then the DB contains the HR dynamic-workflow intent(s)
    # with training phrases and a leave-balance response template
    await seed_hr_data(db_session)
    await db_session.commit()

    # 1. Verify check_leave_balance intent
    stmt = select(Intent).where(Intent.name == "check_leave_balance")
    res = await db_session.execute(stmt)
    intent = res.scalar_one_or_none()

    assert intent is not None
    assert intent.role_pack == "hr"
    assert intent.intent_type == "dynamic_workflow"
    assert intent.needs_retrain is False

    # 2. Verify ~30-50 training phrases exist for this intent
    stmt_phrases = select(TrainingPhrase).where(TrainingPhrase.intent_id == intent.intent_id)
    phrases = (await db_session.execute(stmt_phrases)).scalars().all()
    assert len(phrases) >= 30

    # 3. Verify stub intents
    stmt_status = select(Intent).where(Intent.name == "ask_leave_status")
    status_intent = (await db_session.execute(stmt_status)).scalar_one_or_none()
    assert status_intent is not None
    assert status_intent.role_pack == "hr"
    assert status_intent.intent_type == "dynamic_workflow"

    stmt_req = select(Intent).where(Intent.name == "submit_leave_request")
    req_intent = (await db_session.execute(stmt_req)).scalar_one_or_none()
    assert req_intent is not None
    assert req_intent.role_pack == "hr"
    assert req_intent.intent_type == "dynamic_workflow"

    stmt_faq = select(Intent).where(Intent.name == "ask_policy_faq")
    faq_intent = (await db_session.execute(stmt_faq)).scalar_one_or_none()
    assert faq_intent is not None
    assert faq_intent.role_pack == "hr"
    assert faq_intent.intent_type == "static_faq"

    # 4. Verify response template
    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_leave_balance_response"
    )
    tmpl = (await db_session.execute(stmt_tmpl)).scalar_one_or_none()
    assert tmpl is not None
    assert "{total}" in tmpl.base_text
    assert "total" in tmpl.available_variables
    assert "casual" in tmpl.available_variables
    assert "sick" in tmpl.available_variables
    assert "earned" in tmpl.available_variables

    # 5. Verify response variants
    stmt_variants = select(ResponseVariant).where(
        ResponseVariant.template_id == tmpl.template_id
    )
    variants = (await db_session.execute(stmt_variants)).scalars().all()
    assert len(variants) >= 1
    assert any("{total}" in v.variant_text for v in variants)


@pytest.mark.asyncio
async def test_seed_hr_data_is_idempotent(db_session):
    # Running seed multiple times should not create duplicate intents or templates
    await seed_hr_data(db_session)
    await db_session.commit()

    await seed_hr_data(db_session)
    await db_session.commit()

    stmt = select(Intent).where(Intent.name == "check_leave_balance")
    intents = (await db_session.execute(stmt)).scalars().all()
    assert len(intents) == 1

    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_leave_balance_response"
    )
    tmpls = (await db_session.execute(stmt_tmpl)).scalars().all()
    assert len(tmpls) == 1
