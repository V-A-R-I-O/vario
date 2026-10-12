import pytest
from sqlalchemy import select

from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase
from app.models.response_template import ResponseTemplate
from scripts.seed import seed_admissions_data


@pytest.mark.asyncio
async def test_seed_admissions_data_creates_intents_and_template(db_session):
    # AC 4: DB contains the Admissions dynamic-workflow intent(s) with training phrases and application-status response template
    await seed_admissions_data(db_session)
    await db_session.commit()

    # 1. Verify check_application_status intent
    stmt = select(Intent).where(Intent.name == "check_application_status")
    res = await db_session.execute(stmt)
    intent = res.scalar_one_or_none()

    assert intent is not None
    assert intent.role_pack == "admissions"
    assert intent.intent_type == "dynamic_workflow"
    assert intent.needs_retrain is False

    # 2. Verify training phrases exist for this intent
    stmt_phrases = select(TrainingPhrase).where(TrainingPhrase.intent_id == intent.intent_id)
    phrases = (await db_session.execute(stmt_phrases)).scalars().all()
    assert len(phrases) >= 30

    # 3. Verify stub intents
    stmt_chk = select(Intent).where(Intent.name == "get_document_checklist")
    chk_intent = (await db_session.execute(stmt_chk)).scalar_one_or_none()
    assert chk_intent is not None
    assert chk_intent.role_pack == "admissions"

    stmt_fee = select(Intent).where(Intent.name == "ask_fee_deadline")
    fee_intent = (await db_session.execute(stmt_fee)).scalar_one_or_none()
    assert fee_intent is not None
    assert fee_intent.role_pack == "admissions"

    # 4. Verify response template
    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_response"
    )
    tmpl = (await db_session.execute(stmt_tmpl)).scalar_one_or_none()
    assert tmpl is not None
    assert tmpl.role_pack == "admissions"
    assert "{application_id}" in tmpl.base_text
    assert "{status}" in tmpl.base_text
    assert "{next_step}" in tmpl.base_text


@pytest.mark.asyncio
async def test_seed_admissions_data_is_idempotent(db_session):
    # Running seed multiple times should not create duplicate intents or templates
    await seed_admissions_data(db_session)
    await db_session.commit()

    await seed_admissions_data(db_session)
    await db_session.commit()

    stmt = select(Intent).where(Intent.name == "check_application_status")
    intents = (await db_session.execute(stmt)).scalars().all()
    assert len(intents) == 1

    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_response"
    )
    tmpls = (await db_session.execute(stmt_tmpl)).scalars().all()
    assert len(tmpls) == 1
