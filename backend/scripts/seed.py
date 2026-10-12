import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Engine and sessionmaker
engine = create_async_engine(settings.DATABASE_URL, echo=False)
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
            base_text="You have {balance} days of leave remaining.",
            allow_rephrasing=True,
            available_variables=["balance"],
        )
        session.add(tmpl)
        await session.flush()
        logger.info("Created response template: check_leave_balance_response")

    # 6. Response Variants for check_leave_balance_response
    variants = [
        "You have {balance} days of leave remaining.",
        "Your current leave balance is {balance} days.",
        "You have {balance} days of leave left.",
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

async def seed_admissions_data(session: AsyncSession):
    """Placeholder for Admissions role-pack seed data (slice-05)."""
    logger.info("Seeding Admissions role-pack data...")
    # TODO: Add Admissions intents, phrases, templates
    pass

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
