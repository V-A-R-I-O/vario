import pytest
from sqlalchemy import select

from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from scripts.seed import seed_it_data


@pytest.mark.asyncio
async def test_seed_it_data_creates_status_intent_stubs_and_template(db_session):
    await seed_it_data(db_session)
    await db_session.commit()

    status_result = await db_session.execute(
        select(Intent).where(Intent.name == "check_ticket_status")
    )
    status_intent = status_result.scalar_one_or_none()
    assert status_intent is not None
    assert status_intent.role_pack == "it"
    assert status_intent.intent_type == "dynamic_workflow"
    assert status_intent.needs_retrain is False

    phrase_result = await db_session.execute(
        select(TrainingPhrase).where(TrainingPhrase.intent_id == status_intent.intent_id)
    )
    phrases = phrase_result.scalars().all()
    assert len(phrases) >= 30
    assert any("TKT-1234" in phrase.phrase_text for phrase in phrases)

    for name in ("raise_ticket", "reset_password"):
        result = await db_session.execute(select(Intent).where(Intent.name == name))
        stub = result.scalar_one_or_none()
        assert stub is not None
        assert stub.role_pack == "it"
        assert stub.intent_type == "dynamic_workflow"

    template_result = await db_session.execute(
        select(ResponseTemplate).where(
            ResponseTemplate.template_key == "check_ticket_status_response"
        )
    )
    template = template_result.scalar_one_or_none()
    assert template is not None
    assert template.role_pack == "it"
    assert "{ticket_id}" in template.base_text
    assert "{status}" in template.base_text
    assert "ticket_id" in template.available_variables
    assert "status" in template.available_variables

    variants_result = await db_session.execute(
        select(ResponseVariant).where(ResponseVariant.template_id == template.template_id)
    )
    variants = variants_result.scalars().all()
    assert len(variants) >= 5
    assert all("{ticket_id}" in variant.variant_text for variant in variants)
    assert all("{status}" in variant.variant_text for variant in variants)


@pytest.mark.asyncio
async def test_seed_it_data_is_idempotent(db_session):
    await seed_it_data(db_session)
    await db_session.commit()
    await seed_it_data(db_session)
    await db_session.commit()

    intents_result = await db_session.execute(
        select(Intent).where(Intent.name.in_(["check_ticket_status", "raise_ticket", "reset_password"]))
    )
    assert len(intents_result.scalars().all()) == 3

    status_result = await db_session.execute(
        select(Intent).where(Intent.name == "check_ticket_status")
    )
    status_intent = status_result.scalar_one()
    phrase_result = await db_session.execute(
        select(TrainingPhrase).where(TrainingPhrase.intent_id == status_intent.intent_id)
    )
    assert len(phrase_result.scalars().all()) == 40

    template_result = await db_session.execute(
        select(ResponseTemplate).where(
            ResponseTemplate.template_key == "check_ticket_status_response"
        )
    )
    template = template_result.scalar_one()
    variants_result = await db_session.execute(
        select(ResponseVariant).where(ResponseVariant.template_id == template.template_id)
    )
    assert len(variants_result.scalars().all()) == 5
