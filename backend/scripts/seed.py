import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_async_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

# Engine and sessionmaker
engine = create_async_engine(get_async_db_url(settings.DATABASE_URL), echo=False)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def seed_hr_data(session: AsyncSession):
    """Placeholder for HR role-pack seed data (slice-03)."""
    logger.info("Seeding HR role-pack data...")
    # TODO: Add HR intents, phrases, templates
    pass

async def seed_it_data(session: AsyncSession):
    """Placeholder for IT role-pack seed data (slice-04)."""
    logger.info("Seeding IT role-pack data...")
    # TODO: Add IT intents, phrases, templates
    pass

from sqlalchemy import select
from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant

ADMISSIONS_PHRASES = [
    "what is the status of application APP-1001?",
    "check status of APP-1002",
    "can you check my application APP-1003?",
    "what happened to application APP-1004?",
    "status of APP-1001",
    "I want to check my admission status for APP-1002",
    "track application APP-1003",
    "application status APP-1004",
    "is APP-1001 accepted?",
    "did APP-1002 get approved?",
    "tell me the progress on my application APP-1003",
    "check APP-1004",
    "what is the update on APP-1001?",
    "any news on application APP-1002?",
    "could you look up APP-1003 for me?",
    "lookup application APP-1004",
    "please check my application ID APP-1001",
    "application APP-1002 status please",
    "status check for APP-1003",
    "verify application status for APP-1004",
    "has my application APP-1001 been reviewed?",
    "admission status for reference APP-1002",
    "where does application APP-1003 stand?",
    "how is my application APP-1004 progressing?",
    "what are the next steps for my application APP-1001?",
    "status of my registration APP-1002",
    "query status for APP-1003",
    "I need to check the decision on APP-1004",
    "check application progress APP-1001",
    "what is the admission decision for APP-1002?",
    "can I get a status update on APP-1003?",
    "please check if APP-1004 is under review",
    "check if APP-1001 has been admitted",
    "my application ID is APP-1002, what is the status?",
    "regarding APP-1003, has a decision been made?",
]

ADMISSIONS_STATUS_VARIANTS = [
    "Your application {application_id} is currently {status}. Next step: {next_step}",
    "Application {application_id} status: {status}. Next step is: {next_step}",
    "The status for application {application_id} is {status}. What to do next: {next_step}",
    "Currently, application {application_id} is marked as {status}. Your next step: {next_step}",
    "Regarding your application {application_id}, it is {status}. Next step: {next_step}",
]

ADMISSIONS_NOT_FOUND_VARIANTS = [
    "Application {application_id} was not found. Suggested next step: {suggested_next_step}",
    "We couldn't find an application with ID {application_id}. Suggested next step: {suggested_next_step}",
    "No records found for application {application_id}. Next step: {suggested_next_step}",
    "Application reference {application_id} could not be located. What to do next: {suggested_next_step}",
    "Unable to locate application {application_id}. Suggested next step: {suggested_next_step}",
]

async def seed_admissions_data(session: AsyncSession):
    """Seed Admissions role-pack intents, phrases, and response templates (slice-22)."""
    logger.info("Seeding Admissions role-pack data...")

    # 1. Main Intent: check_application_status
    stmt = select(Intent).where(Intent.name == "check_application_status")
    res = await session.execute(stmt)
    status_intent = res.scalar_one_or_none()
    if not status_intent:
        status_intent = Intent(
            role_pack="admissions",
            name="check_application_status",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(status_intent)
        await session.flush()
        logger.info("Created intent: check_application_status")

    # Seed training phrases for check_application_status
    for phrase_text in ADMISSIONS_PHRASES:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == status_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=status_intent.intent_id, phrase_text=phrase_text))

    # 2. Stub Intent: get_document_checklist (placeholder for slice-25)
    stmt_chk = select(Intent).where(Intent.name == "get_document_checklist")
    res_chk = await session.execute(stmt_chk)
    if not res_chk.scalar_one_or_none():
        chk_intent = Intent(
            role_pack="admissions",
            name="get_document_checklist",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(chk_intent)
        await session.flush()
        session.add(TrainingPhrase(intent_id=chk_intent.intent_id, phrase_text="what documents do I need for btech?"))
        session.add(TrainingPhrase(intent_id=chk_intent.intent_id, phrase_text="document checklist for admission"))
        logger.info("Created stub intent: get_document_checklist")

    # 3. Stub Intent: ask_fee_deadline (placeholder for slice-26)
    stmt_fee = select(Intent).where(Intent.name == "ask_fee_deadline")
    res_fee = await session.execute(stmt_fee)
    if not res_fee.scalar_one_or_none():
        fee_intent = Intent(
            role_pack="admissions",
            name="ask_fee_deadline",
            intent_type="static_faq",
            needs_retrain=False,
        )
        session.add(fee_intent)
        await session.flush()
        session.add(TrainingPhrase(intent_id=fee_intent.intent_id, phrase_text="when is the deadline to pay fees?"))
        session.add(TrainingPhrase(intent_id=fee_intent.intent_id, phrase_text="what is the tuition fee for BTech?"))
        logger.info("Created stub intent: ask_fee_deadline")

    # 4. Response Template: check_application_status_response + 5 variants
    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_response"
    )
    res_tmpl = await session.execute(stmt_tmpl)
    tmpl = res_tmpl.scalar_one_or_none()
    if not tmpl:
        tmpl = ResponseTemplate(
            role_pack="admissions",
            template_key="check_application_status_response",
            base_text="Your application {application_id} is currently {status}. Next step: {next_step}",
            allow_rephrasing=True,
            available_variables=["application_id", "status", "next_step"],
        )
        session.add(tmpl)
        await session.flush()
        logger.info("Created response template: check_application_status_response")

    # Seed 5 variants for check_application_status_response
    for var_text in ADMISSIONS_STATUS_VARIANTS:
        stmt_var = select(ResponseVariant).where(
            ResponseVariant.template_id == tmpl.template_id,
            ResponseVariant.variant_text == var_text,
        )
        existing_var = (await session.execute(stmt_var)).scalar_one_or_none()
        if not existing_var:
            session.add(ResponseVariant(template_id=tmpl.template_id, variant_text=var_text))

    # 5. Response Template: check_application_status_not_found_response + 5 variants (FR-17)
    stmt_tmpl_nf = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_application_status_not_found_response"
    )
    res_tmpl_nf = await session.execute(stmt_tmpl_nf)
    tmpl_nf = res_tmpl_nf.scalar_one_or_none()
    if not tmpl_nf:
        tmpl_nf = ResponseTemplate(
            role_pack="admissions",
            template_key="check_application_status_not_found_response",
            base_text="Application {application_id} was not found. Suggested next step: {suggested_next_step}",
            allow_rephrasing=True,
            available_variables=["application_id", "suggested_next_step"],
        )
        session.add(tmpl_nf)
        await session.flush()
        logger.info("Created response template: check_application_status_not_found_response")

    # Seed 5 variants for check_application_status_not_found_response
    for var_text in ADMISSIONS_NOT_FOUND_VARIANTS:
        stmt_var_nf = select(ResponseVariant).where(
            ResponseVariant.template_id == tmpl_nf.template_id,
            ResponseVariant.variant_text == var_text,
        )
        existing_var_nf = (await session.execute(stmt_var_nf)).scalar_one_or_none()
        if not existing_var_nf:
            session.add(ResponseVariant(template_id=tmpl_nf.template_id, variant_text=var_text))

async def main():
    logger.info(f"Connecting to database at {settings.DATABASE_URL}")
    async with AsyncSessionLocal() as session:
        # Run role-pack seeders
        await seed_hr_data(session)
        await seed_it_data(session)
        await seed_admissions_data(session)
        
        await session.commit()
    logger.info("Database seeding complete.")

if __name__ == "__main__":
    asyncio.run(main())
