import pytest
from sqlalchemy import select

from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from app.services import response_renderer
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
    assert fee_intent.intent_type == "dynamic_workflow"

    stmt_fee_phrases = select(TrainingPhrase).where(TrainingPhrase.intent_id == fee_intent.intent_id)
    fee_phrases = (await db_session.execute(stmt_fee_phrases)).scalars().all()
    assert len(fee_phrases) >= 20

    # 4. Verify check_application_status_response template and 5 variants
    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_response"
    )
    tmpl = (await db_session.execute(stmt_tmpl)).scalar_one_or_none()
    assert tmpl is not None
    assert tmpl.role_pack == "admissions"
    assert "{application_id}" in tmpl.base_text
    assert "{status}" in tmpl.base_text
    assert "{next_step}" in tmpl.base_text

    stmt_vars = select(ResponseVariant).where(ResponseVariant.template_id == tmpl.template_id)
    status_variants = (await db_session.execute(stmt_vars)).scalars().all()
    assert len(status_variants) == 5
    for var in status_variants:
        assert "{application_id}" in var.variant_text
        assert "{status}" in var.variant_text
        assert "{next_step}" in var.variant_text

    # 5. Verify check_application_status_not_found_response template and 5 variants (FR-17)
    stmt_tmpl_nf = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_not_found_response"
    )
    tmpl_nf = (await db_session.execute(stmt_tmpl_nf)).scalar_one_or_none()
    assert tmpl_nf is not None
    assert tmpl_nf.role_pack == "admissions"
    assert "{application_id}" in tmpl_nf.base_text
    assert "{suggested_next_step}" in tmpl_nf.base_text

    stmt_vars_nf = select(ResponseVariant).where(ResponseVariant.template_id == tmpl_nf.template_id)
    nf_variants = (await db_session.execute(stmt_vars_nf)).scalars().all()
    assert len(nf_variants) == 5
    for var in nf_variants:
        assert "{application_id}" in var.variant_text
        assert "{suggested_next_step}" in var.variant_text

    # 6. Verify get_document_checklist_response template and 5 variants (slice-25)
    stmt_tmpl_chk = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "get_document_checklist_response"
    )
    tmpl_chk = (await db_session.execute(stmt_tmpl_chk)).scalar_one_or_none()
    assert tmpl_chk is not None
    assert tmpl_chk.role_pack == "admissions"
    assert "{program}" in tmpl_chk.base_text
    assert "{items_summary}" in tmpl_chk.base_text

    stmt_vars_chk = select(ResponseVariant).where(ResponseVariant.template_id == tmpl_chk.template_id)
    chk_variants = (await db_session.execute(stmt_vars_chk)).scalars().all()
    assert len(chk_variants) == 5
    for var in chk_variants:
        assert "{program}" in var.variant_text
        assert "{items_summary}" in var.variant_text

    # 7. Verify get_document_checklist_not_found_response template and 5 variants (slice-25)
    stmt_tmpl_chk_nf = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "get_document_checklist_not_found_response"
    )
    tmpl_chk_nf = (await db_session.execute(stmt_tmpl_chk_nf)).scalar_one_or_none()
    assert tmpl_chk_nf is not None
    assert tmpl_chk_nf.role_pack == "admissions"
    assert "{program}" in tmpl_chk_nf.base_text

    stmt_vars_chk_nf = select(ResponseVariant).where(ResponseVariant.template_id == tmpl_chk_nf.template_id)
    chk_nf_variants = (await db_session.execute(stmt_vars_chk_nf)).scalars().all()
    assert len(chk_nf_variants) == 5
    for var in chk_nf_variants:
        assert "{program}" in var.variant_text

    # 8. Verify ask_fee_deadline_response template and 5 variants (slice-26)
    stmt_tmpl_fee = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "ask_fee_deadline_response"
    )
    tmpl_fee = (await db_session.execute(stmt_tmpl_fee)).scalar_one_or_none()
    assert tmpl_fee is not None
    assert tmpl_fee.role_pack == "admissions"
    assert "{academic_year}" in tmpl_fee.base_text
    assert "{details}" in tmpl_fee.base_text

    stmt_vars_fee = select(ResponseVariant).where(ResponseVariant.template_id == tmpl_fee.template_id)
    fee_variants = (await db_session.execute(stmt_vars_fee)).scalars().all()
    assert len(fee_variants) == 5
    for var in fee_variants:
        assert "{academic_year}" in var.variant_text
        assert "{details}" in var.variant_text

    # 9. Verify response renderer renders templates with slot values
    rendered_status = await response_renderer.render(
        db_session,
        "check_application_status_response",
        {"application_id": "APP-1001", "status": "Under Review", "next_step": "Decision in 2 weeks"},
    )
    assert "APP-1001" in rendered_status
    assert "Under Review" in rendered_status
    assert "Decision in 2 weeks" in rendered_status

    rendered_nf = await response_renderer.render(
        db_session,
        "check_application_status_not_found_response",
        {"application_id": "APP-9999", "suggested_next_step": "contact admissions@org.example.com"},
    )
    assert "APP-9999" in rendered_nf
    assert "contact admissions@org.example.com" in rendered_nf

    rendered_chk = await response_renderer.render(
        db_session,
        "get_document_checklist_response",
        {"program": "Computer Science (B.Tech)", "items_summary": "Class 10 Marksheet, Class 12 Marksheet"},
    )
    assert "Computer Science (B.Tech)" in rendered_chk
    assert "Class 10 Marksheet" in rendered_chk

    rendered_chk_nf = await response_renderer.render(
        db_session,
        "get_document_checklist_not_found_response",
        {"program": "Aerospace Engineering"},
    )
    assert "Aerospace Engineering" in rendered_chk_nf

    rendered_fee = await response_renderer.render(
        db_session,
        "ask_fee_deadline_response",
        {"academic_year": "2026-2027", "details": "Application Fee: ₹1,500"},
    )
    assert "2026-2027" in rendered_fee
    assert "Application Fee: ₹1,500" in rendered_fee


@pytest.mark.asyncio
async def test_seed_admissions_data_is_idempotent(db_session):
    # Running seed multiple times should not create duplicate intents, templates, or variants
    await seed_admissions_data(db_session)
    await db_session.commit()

    await seed_admissions_data(db_session)
    await db_session.commit()

    stmt = select(Intent).where(Intent.name == "check_application_status")
    intents = (await db_session.execute(stmt)).scalars().all()
    assert len(intents) == 1

    stmt_chk = select(Intent).where(Intent.name == "get_document_checklist")
    chk_intents = (await db_session.execute(stmt_chk)).scalars().all()
    assert len(chk_intents) == 1

    stmt_fee = select(Intent).where(Intent.name == "ask_fee_deadline")
    fee_intents = (await db_session.execute(stmt_fee)).scalars().all()
    assert len(fee_intents) == 1

    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_response"
    )
    tmpls = (await db_session.execute(stmt_tmpl)).scalars().all()
    assert len(tmpls) == 1

    stmt_tmpl_chk = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "get_document_checklist_response"
    )
    tmpls_chk = (await db_session.execute(stmt_tmpl_chk)).scalars().all()
    assert len(tmpls_chk) == 1

    stmt_vars_chk = select(ResponseVariant).where(ResponseVariant.template_id == tmpls_chk[0].template_id)
    vars_chk = (await db_session.execute(stmt_vars_chk)).scalars().all()
    assert len(vars_chk) == 5

    stmt_tmpl_fee = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "ask_fee_deadline_response"
    )
    tmpls_fee = (await db_session.execute(stmt_tmpl_fee)).scalars().all()
    assert len(tmpls_fee) == 1

    stmt_vars_fee = select(ResponseVariant).where(ResponseVariant.template_id == tmpls_fee[0].template_id)
    vars_fee = (await db_session.execute(stmt_vars_fee)).scalars().all()
    assert len(vars_fee) == 5

