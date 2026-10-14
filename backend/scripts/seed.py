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

from sqlalchemy import select
from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant

HR_LEAVE_BALANCE_PHRASES = [
    "what is my leave balance?",
    "what's my leave balance",
    "what is my current leave balance?",
    "check my leave balance",
    "how many leaves do I have left?",
    "how many vacation days do I have remaining?",
    "can you tell me my leave balance?",
    "show me my leave balance",
    "I want to check my leave balance",
    "how many days of leave do I have?",
    "how much PTO do I have left?",
    "check my PTO balance",
    "what is my remaining paid time off?",
    "how many annual leave days do I have?",
    "check annual leave balance",
    "how much annual leave is remaining?",
    "how many sick days do I have left?",
    "check sick leave balance",
    "what's my sick leave balance?",
    "do I have any casual leave left?",
    "how many casual leaves do I have?",
    "how many vacation days are available?",
    "tell me my remaining vacation balance",
    "leave balance inquiry",
    "can I check my remaining time off?",
    "how many holidays or leaves do I have left?",
    "what is my total available leave?",
    "could you check how much leave I have left?",
    "check remaining leave days for me",
    "how many paid leaves are left in my account?",
    "what is my vacation allowance balance?",
    "how many PTO hours or days do I have?",
    "I'd like to see my current leave balance",
    "please show how many leaves I have remaining",
    "check my balance for paid time off",
    "how much time off do I have left?",
    "what's my PTO balance right now?",
    "view my leave balance",
    "check my remaining vacation days",
    "how much leave can I take?",
    "how many days off do I have available?",
]

async def seed_hr_data(session: AsyncSession):
    """Seed HR role-pack intents, training phrases, and response templates (slice-12)."""
    logger.info("Seeding HR role-pack data...")

    # 1. Main Intent: check_leave_balance
    stmt = select(Intent).where(Intent.name == "check_leave_balance")
    res = await session.execute(stmt)
    status_intent = res.scalar_one_or_none()
    if not status_intent:
        status_intent = Intent(
            role_pack="hr",
            name="check_leave_balance",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(status_intent)
        await session.flush()
        logger.info("Created intent: check_leave_balance")

    # Seed training phrases for check_leave_balance
    for phrase_text in HR_LEAVE_BALANCE_PHRASES:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == status_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=status_intent.intent_id, phrase_text=phrase_text))

    # 2. Stub Intent: ask_leave_status (placeholder for later slice)
    stmt_status = select(Intent).where(Intent.name == "ask_leave_status")
    res_status = await session.execute(stmt_status)
    if not res_status.scalar_one_or_none():
        status_stub = Intent(
            role_pack="hr",
            name="ask_leave_status",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(status_stub)
        await session.flush()
        session.add(TrainingPhrase(intent_id=status_stub.intent_id, phrase_text="what is the status of my leave request?"))
        session.add(TrainingPhrase(intent_id=status_stub.intent_id, phrase_text="check my leave application status"))
        logger.info("Created stub intent: ask_leave_status")

    # 3. Stub Intent: submit_leave_request (placeholder for slice-15)
    stmt_req = select(Intent).where(Intent.name == "submit_leave_request")
    res_req = await session.execute(stmt_req)
    if not res_req.scalar_one_or_none():
        req_stub = Intent(
            role_pack="hr",
            name="submit_leave_request",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(req_stub)
        await session.flush()
        session.add(TrainingPhrase(intent_id=req_stub.intent_id, phrase_text="I want to apply for leave"))
        session.add(TrainingPhrase(intent_id=req_stub.intent_id, phrase_text="submit a leave request"))
        logger.info("Created stub intent: submit_leave_request")

    # 4. Stub Intent: ask_policy_faq (placeholder for slice-16)
    stmt_faq = select(Intent).where(Intent.name == "ask_policy_faq")
    res_faq = await session.execute(stmt_faq)
    if not res_faq.scalar_one_or_none():
        faq_stub = Intent(
            role_pack="hr",
            name="ask_policy_faq",
            intent_type="static_faq",
            needs_retrain=False,
        )
        session.add(faq_stub)
        await session.flush()
        session.add(TrainingPhrase(intent_id=faq_stub.intent_id, phrase_text="what is the company leave policy?"))
        session.add(TrainingPhrase(intent_id=faq_stub.intent_id, phrase_text="how many sick days are allowed per year?"))
        logger.info("Created stub intent: ask_policy_faq")

    # 5. Response Template: check_leave_balance_response
    stmt_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "check_leave_balance_response"
    )
    res_tmpl = await session.execute(stmt_tmpl)
    tmpl = res_tmpl.scalar_one_or_none()
    if not tmpl:
        tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="check_leave_balance_response",
            base_text="You have {total} days of leave remaining: {casual} casual, {sick} sick, {earned} earned.",
            allow_rephrasing=True,
            available_variables=["total", "casual", "sick", "earned", "employee_id"],
        )
        session.add(tmpl)
        await session.flush()
        logger.info("Created response template: check_leave_balance_response")

    # 6. Response Variants for check_leave_balance_response
    variants = [
        "You have {total} days of leave remaining: {casual} casual, {sick} sick, {earned} earned.",
        "Your current leave balance is {total} days ({casual} casual, {sick} sick, {earned} earned).",
        "You have {total} days of leave left — {casual} casual, {sick} sick, and {earned} earned.",
        "Your leave balance: {total} days total. Breakdown: {casual} casual, {sick} sick, {earned} earned.",
        "You currently have {total} days available: {casual} casual days, {sick} sick days, and {earned} earned days.",
    ]
    for variant_text in variants:
        variant_stmt = select(ResponseVariant).where(
            ResponseVariant.template_id == tmpl.template_id,
            ResponseVariant.variant_text == variant_text,
        )
        existing_variant = await session.execute(variant_stmt)
        if not existing_variant.scalar_one_or_none():
            session.add(ResponseVariant(template_id=tmpl.template_id, variant_text=variant_text))
            logger.info("Created response variant for check_leave_balance_response")

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

ADMISSIONS_CHECKLIST_PHRASES = [
    "what documents do I need for btech?",
    "document checklist for Computer Science",
    "which certificates are required for mtech?",
    "checklist of documents for mba",
    "what do I need to submit for Data Science?",
    "document requirements for btech",
    "list of documents needed for admission",
    "show me the checklist for mba",
    "what papers are required for mtech admission?",
    "mandatory documents for Computer Science (B.Tech)",
    "what documents are required?",
    "can you show the document checklist?",
    "what certificates do I need to submit?",
    "documents required for admission",
    "admission document requirements",
    "required documents for btech admission",
    "checklist for mtech program",
    "what are the necessary papers for mba?",
]

ADMISSIONS_CHECKLIST_VARIANTS = [
    "Here are the required documents for {program}: {items_summary}",
    "Required documents for {program}: {items_summary}",
    "For admission to {program}, please prepare: {items_summary}",
    "Here is the document checklist for {program}: {items_summary}",
    "The required documents for {program} admission are: {items_summary}",
]

ADMISSIONS_CHECKLIST_NOT_FOUND_VARIANTS = [
    "No document checklist found for program '{program}'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
    "We could not find a checklist for '{program}'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
    "Program '{program}' was not found. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
    "Checklist unavailable for '{program}'. Supported programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
    "Could not locate document checklist for '{program}'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
]

async def seed_admissions_data(session: AsyncSession):
    """Seed Admissions role-pack intents, phrases, and response templates (slice-22, slice-25)."""
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

    # 2. Intent: get_document_checklist (slice-25)
    stmt_chk = select(Intent).where(Intent.name == "get_document_checklist")
    res_chk = await session.execute(stmt_chk)
    chk_intent = res_chk.scalar_one_or_none()
    if not chk_intent:
        chk_intent = Intent(
            role_pack="admissions",
            name="get_document_checklist",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(chk_intent)
        await session.flush()
        logger.info("Created intent: get_document_checklist")

    # Seed training phrases for get_document_checklist
    for phrase_text in ADMISSIONS_CHECKLIST_PHRASES:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == chk_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=chk_intent.intent_id, phrase_text=phrase_text))

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

    # 6. Response Template: get_document_checklist_response + 5 variants (slice-25)
    stmt_tmpl_chk = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "get_document_checklist_response"
    )
    res_tmpl_chk = await session.execute(stmt_tmpl_chk)
    tmpl_chk = res_tmpl_chk.scalar_one_or_none()
    if not tmpl_chk:
        tmpl_chk = ResponseTemplate(
            role_pack="admissions",
            template_key="get_document_checklist_response",
            base_text="Here are the required documents for {program}: {items_summary}",
            allow_rephrasing=True,
            available_variables=["program", "items_summary"],
        )
        session.add(tmpl_chk)
        await session.flush()
        logger.info("Created response template: get_document_checklist_response")

    for var_text in ADMISSIONS_CHECKLIST_VARIANTS:
        stmt_var_chk = select(ResponseVariant).where(
            ResponseVariant.template_id == tmpl_chk.template_id,
            ResponseVariant.variant_text == var_text,
        )
        existing_var_chk = (await session.execute(stmt_var_chk)).scalar_one_or_none()
        if not existing_var_chk:
            session.add(ResponseVariant(template_id=tmpl_chk.template_id, variant_text=var_text))

    # 7. Response Template: get_document_checklist_not_found_response + 5 variants (slice-25)
    stmt_tmpl_chk_nf = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "get_document_checklist_not_found_response"
    )
    res_tmpl_chk_nf = await session.execute(stmt_tmpl_chk_nf)
    tmpl_chk_nf = res_tmpl_chk_nf.scalar_one_or_none()
    if not tmpl_chk_nf:
        tmpl_chk_nf = ResponseTemplate(
            role_pack="admissions",
            template_key="get_document_checklist_not_found_response",
            base_text="No document checklist found for program '{program}'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
            allow_rephrasing=True,
            available_variables=["program"],
        )
        session.add(tmpl_chk_nf)
        await session.flush()
        logger.info("Created response template: get_document_checklist_not_found_response")

    for var_text in ADMISSIONS_CHECKLIST_NOT_FOUND_VARIANTS:
        stmt_var_chk_nf = select(ResponseVariant).where(
            ResponseVariant.template_id == tmpl_chk_nf.template_id,
            ResponseVariant.variant_text == var_text,
        )
        existing_var_chk_nf = (await session.execute(stmt_var_chk_nf)).scalar_one_or_none()
        if not existing_var_chk_nf:
            session.add(ResponseVariant(template_id=tmpl_chk_nf.template_id, variant_text=var_text))

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
