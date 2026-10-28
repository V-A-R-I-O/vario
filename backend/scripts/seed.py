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

    # 3. Intent: submit_leave_request (slice-15)
    stmt_req = select(Intent).where(Intent.name == "submit_leave_request")
    res_req = await session.execute(stmt_req)
    submit_intent = res_req.scalar_one_or_none()
    if not submit_intent:
        submit_intent = Intent(
            role_pack="hr",
            name="submit_leave_request",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(submit_intent)
        await session.flush()
        logger.info("Created intent: submit_leave_request")

    # Training phrases for submit_leave_request
    leave_request_phrases = [
        "I want to apply for leave",
        "submit a leave request",
        "apply for leave",
        "request time off",
        "I need to take leave",
        "book leave",
        "submit leave application",
        "apply for vacation",
        "request leave",
        "I want to submit a leave application",
    ]
    for phrase_text in leave_request_phrases:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == submit_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=submit_intent.intent_id, phrase_text=phrase_text))

    # 4. Intent: ask_policy_faq (slice-16)
    stmt_faq = select(Intent).where(Intent.name == "ask_policy_faq")
    res_faq = await session.execute(stmt_faq)
    faq_intent = res_faq.scalar_one_or_none()
    if not faq_intent:
        faq_intent = Intent(
            role_pack="hr",
            name="ask_policy_faq",
            intent_type="static_faq",
            needs_retrain=False,
        )
        session.add(faq_intent)
        await session.flush()
        logger.info("Created intent: ask_policy_faq")

    faq_phrases = [
        "what is the company leave policy?",
        "how many sick days are allowed per year?",
        "what is the policy for maternity leave?",
        "can I carry forward unused leaves to next year?",
        "what are the rules for taking sick leave?",
        "how many days of paternity leave do I get?",
        "tell me about the bereavement leave guidelines",
        "what is the leave carry forward policy?",
        "how many annual leaves are granted per year?",
        "how does maternity leave work?",
        "rules for casual leave and sick leave",
        "company leave policy and rules",
    ]
    for phrase_text in faq_phrases:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == faq_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=faq_intent.intent_id, phrase_text=phrase_text))

    # 4b. Intent: ask_wfh_policy (slice-16)
    stmt_wfh = select(Intent).where(Intent.name == "ask_wfh_policy")
    res_wfh = await session.execute(stmt_wfh)
    wfh_intent = res_wfh.scalar_one_or_none()
    if not wfh_intent:
        wfh_intent = Intent(
            role_pack="hr",
            name="ask_wfh_policy",
            intent_type="static_faq",
            needs_retrain=False,
        )
        session.add(wfh_intent)
        await session.flush()
        logger.info("Created intent: ask_wfh_policy")

    wfh_phrases = [
        "what is the WFH policy?",
        "what's the WFH policy?",
        "what is the work from home policy?",
        "can I work from home?",
        "how many days can I work remotely?",
        "tell me about the remote work policy",
        "work from home policy",
        "are we allowed to work from home?",
        "remote work guidelines",
        "guidelines for working from home",
        "do we have a work from home policy?",
        "how does work from home work here?",
    ]
    for phrase_text in wfh_phrases:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == wfh_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=wfh_intent.intent_id, phrase_text=phrase_text))

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

    # 7. Response Template: submit_leave_slot_prompt (slice-15)
    stmt_slot_prompt = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "submit_leave_slot_prompt"
    )
    res_slot_prompt = await session.execute(stmt_slot_prompt)
    slot_prompt_tmpl = res_slot_prompt.scalar_one_or_none()
    if not slot_prompt_tmpl:
        slot_prompt_tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="submit_leave_slot_prompt",
            base_text="What type of leave would you like to request?",
            allow_rephrasing=False,
            available_variables=["requested_slot"],
        )
        session.add(slot_prompt_tmpl)
        await session.flush()
        logger.info("Created response template: submit_leave_slot_prompt")

    # 8. Response Template: submit_leave_confirmation (slice-15)
    stmt_confirmation = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "submit_leave_confirmation"
    )
    res_confirmation = await session.execute(stmt_confirmation)
    confirmation_tmpl = res_confirmation.scalar_one_or_none()
    if not confirmation_tmpl:
        confirmation_tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="submit_leave_confirmation",
            base_text="Please confirm your leave request: {leave_type} leave from {start_date} to {end_date}. Reason: {reason}",
            allow_rephrasing=True,
            available_variables=["leave_type", "start_date", "end_date", "reason"],
        )
        session.add(confirmation_tmpl)
        await session.flush()
        logger.info("Created response template: submit_leave_confirmation")

    # Confirmation variants
    confirmation_variants = [
        "Please confirm your leave request: {leave_type} leave from {start_date} to {end_date}. Reason: {reason}",
        "Ready to submit? {leave_type} leave, {start_date} to {end_date}. Reason: {reason}",
        "Review your request: {leave_type} leave starting {start_date}, ending {end_date}. Reason: {reason}",
    ]
    for variant_text in confirmation_variants:
        variant_stmt = select(ResponseVariant).where(
            ResponseVariant.template_id == confirmation_tmpl.template_id,
            ResponseVariant.variant_text == variant_text,
        )
        existing_variant = await session.execute(variant_stmt)
        if not existing_variant.scalar_one_or_none():
            session.add(ResponseVariant(template_id=confirmation_tmpl.template_id, variant_text=variant_text))

    # 9. Response Template: submit_leave_result (slice-15)
    stmt_result = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "submit_leave_result"
    )
    res_result = await session.execute(stmt_result)
    result_tmpl = res_result.scalar_one_or_none()
    if not result_tmpl:
        result_tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="submit_leave_result",
            base_text="Leave request submitted successfully! Reference ID: {reference_id}",
            allow_rephrasing=True,
            available_variables=["reference_id", "leave_type", "start_date", "end_date", "days"],
        )
        session.add(result_tmpl)
        await session.flush()
        logger.info("Created response template: submit_leave_result")

    # Result variants
    result_variants = [
        "Leave request submitted successfully! Reference ID: {reference_id}",
        "Your leave application has been submitted. Reference: {reference_id}",
        "All set! Your leave request reference is {reference_id}.",
        "Leave request created with reference ID {reference_id}.",
    ]
    for variant_text in result_variants:
        variant_stmt = select(ResponseVariant).where(
            ResponseVariant.template_id == result_tmpl.template_id,
            ResponseVariant.variant_text == variant_text,
        )
        existing_variant = await session.execute(variant_stmt)
        if not existing_variant.scalar_one_or_none():
            session.add(ResponseVariant(template_id=result_tmpl.template_id, variant_text=variant_text))

    # 10. Response Template: submit_leave_cancelled (slice-15)
    stmt_cancelled = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "submit_leave_cancelled"
    )
    res_cancelled = await session.execute(stmt_cancelled)
    cancelled_tmpl = res_cancelled.scalar_one_or_none()
    if not cancelled_tmpl:
        cancelled_tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="submit_leave_cancelled",
            base_text="Leave request cancelled. No changes were made.",
            allow_rephrasing=False,
            available_variables=[],
        )
        session.add(cancelled_tmpl)
        await session.flush()
        logger.info("Created response template: submit_leave_cancelled")

    # 11. Response Template: ask_policy_faq_response (slice-16)
    stmt_policy_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "ask_policy_faq_response"
    )
    res_policy_tmpl = await session.execute(stmt_policy_tmpl)
    policy_tmpl = res_policy_tmpl.scalar_one_or_none()
    if not policy_tmpl:
        policy_tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="ask_policy_faq_response",
            base_text="Our company leave policy grants 20 annual leaves, 10 sick leaves, and 5 casual leaves per year. Unused annual leaves can be carried forward up to 5 days.",
            allow_rephrasing=True,
            available_variables=[],
        )
        session.add(policy_tmpl)
        await session.flush()
        logger.info("Created response template: ask_policy_faq_response")

    policy_variants = [
        "Our company leave policy grants 20 annual leaves, 10 sick leaves, and 5 casual leaves per year. Unused annual leaves can be carried forward up to 5 days.",
        "Employees receive 20 annual, 10 sick, and 5 casual leave days annually. Up to 5 unused annual leave days roll over.",
        "The leave policy provides 20 annual, 10 sick, and 5 casual days per calendar year, with a maximum of 5 annual days carried forward.",
        "Under our leave policy, you get 20 annual, 10 sick, and 5 casual leave days per year. Unused annual leave carries over up to 5 days.",
        "Standard leave allotment is 20 annual, 10 sick, and 5 casual days per year. Up to 5 unused annual leave days can be carried forward.",
    ]
    for variant_text in policy_variants:
        variant_stmt = select(ResponseVariant).where(
            ResponseVariant.template_id == policy_tmpl.template_id,
            ResponseVariant.variant_text == variant_text,
        )
        existing_variant = await session.execute(variant_stmt)
        if not existing_variant.scalar_one_or_none():
            session.add(ResponseVariant(template_id=policy_tmpl.template_id, variant_text=variant_text))

    # 12. Response Template: ask_wfh_policy_response (slice-16)
    stmt_wfh_tmpl = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "ask_wfh_policy_response"
    )
    res_wfh_tmpl = await session.execute(stmt_wfh_tmpl)
    wfh_tmpl = res_wfh_tmpl.scalar_one_or_none()
    if not wfh_tmpl:
        wfh_tmpl = ResponseTemplate(
            role_pack="hr",
            template_key="ask_wfh_policy_response",
            base_text="Employees may work from home up to 3 days per week, subject to manager approval. Core hours (10am–4pm) apply regardless of location.",
            allow_rephrasing=True,
            available_variables=[],
        )
        session.add(wfh_tmpl)
        await session.flush()
        logger.info("Created response template: ask_wfh_policy_response")

    wfh_variants = [
        "Employees may work from home up to 3 days per week, subject to manager approval. Core hours (10am–4pm) apply regardless of location.",
        "Our WFH policy allows working from home up to 3 days per week with manager approval. Core hours are 10am to 4pm.",
        "You are eligible to work from home up to 3 days each week, approved by your manager. Core hours remain 10:00 AM – 4:00 PM.",
        "Remote work is permitted up to 3 days per week with managerial consent, adhering to core hours (10am–4pm).",
        "Under company policy, you may work remotely up to 3 days per week upon manager approval. Core hours apply.",
    ]
    for variant_text in wfh_variants:
        variant_stmt = select(ResponseVariant).where(
            ResponseVariant.template_id == wfh_tmpl.template_id,
            ResponseVariant.variant_text == variant_text,
        )
        existing_variant = await session.execute(variant_stmt)
        if not existing_variant.scalar_one_or_none():
            session.add(ResponseVariant(template_id=wfh_tmpl.template_id, variant_text=variant_text))

IT_TICKET_STATUS_PHRASES = [
    "what is the status of my ticket TKT-1234?",
    "what's happening with ticket TKT-1234?",
    "check the status of TKT-1234",
    "can you check my ticket TKT-1234?",
    "track ticket TKT-1234",
    "give me an update on ticket TKT-1234",
    "has my ticket TKT-1234 been resolved?",
    "is ticket TKT-1234 still open?",
    "is my IT ticket TKT-1234 closed?",
    "what is the progress of TKT-1234?",
    "please look up ticket TKT-1234",
    "show me the current status of TKT-1234",
    "I need an update for TKT-1234",
    "where does ticket TKT-1234 stand?",
    "when will ticket TKT-1234 be fixed?",
    "has anyone worked on TKT-1234?",
    "check my IT support request TKT-1234",
    "what's the latest on my support ticket TKT-1234?",
    "is there any update on TKT-1234?",
    "tell me whether TKT-1234 is pending",
    "find the status of support request TKT-1234",
    "I want to follow up on TKT-1234",
    "can I get the status for TKT-1234?",
    "ticket TKT-1234 status",
    "status update for TKT-1234",
    "please track my support issue TKT-1234",
    "has the issue in TKT-1234 been fixed?",
    "check if ticket TKT-1234 is in progress",
    "what stage is my ticket TKT-1234 at?",
    "is TKT-1234 assigned to someone?",
    "look up the progress of my ticket TKT-1234",
    "I would like to know the status of TKT-1234",
    "could you tell me if TKT-1234 is resolved?",
    "is my help desk request TKT-1234 complete?",
    "check the progress of IT request TKT-1234",
    "please provide a status update for ticket TKT-1234",
    "do you have news about TKT-1234?",
    "what is the current state of my incident TKT-1234",
    "I am following up on support ticket TKT-1234",
    "tell me the status of my issue TKT-1234",
]

IT_RAISE_TICKET_PHRASES = [
    "I need to raise an IT ticket",
    "create a support ticket",
    "open a new IT ticket",
    "report a technical issue",
    "I need help with my laptop",
    "raise an incident for me",
]

IT_RESET_PASSWORD_PHRASES = [
    "I forgot my password",
    "help me reset my password",
    "I cannot sign in to my account",
    "reset my work account password",
    "I am locked out of my account",
    "how can I change my password?",
]


async def seed_it_data(session: AsyncSession):
    """Seed IT role-pack intents, phrases, and ticket-status response template (slice-17)."""
    logger.info("Seeding IT role-pack data...")

    intents = [
        ("check_ticket_status", "dynamic_workflow", IT_TICKET_STATUS_PHRASES),
        ("raise_ticket", "dynamic_workflow", IT_RAISE_TICKET_PHRASES),
        ("reset_password", "dynamic_workflow", IT_RESET_PASSWORD_PHRASES),
    ]

    for intent_name, intent_type, phrases in intents:
        result = await session.execute(select(Intent).where(Intent.name == intent_name))
        intent = result.scalar_one_or_none()
        if intent is None:
            intent = Intent(
                role_pack="it",
                name=intent_name,
                intent_type=intent_type,
                needs_retrain=False,
            )
            session.add(intent)
            await session.flush()
        elif intent.role_pack != "it":
            raise ValueError(f"Intent name {intent_name!r} already belongs to another role pack")

        for phrase_text in phrases:
            result = await session.execute(
                select(TrainingPhrase).where(
                    TrainingPhrase.intent_id == intent.intent_id,
                    TrainingPhrase.phrase_text == phrase_text,
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(TrainingPhrase(intent_id=intent.intent_id, phrase_text=phrase_text))

    template_key = "check_ticket_status_response"
    result = await session.execute(
        select(ResponseTemplate).where(ResponseTemplate.template_key == template_key)
    )
    template = result.scalar_one_or_none()
    if template is None:
        template = ResponseTemplate(
            role_pack="it",
            template_key=template_key,
            base_text="Ticket {ticket_id} is currently {status}.",
            allow_rephrasing=True,
            available_variables=["ticket_id", "status"],
        )
        session.add(template)
        await session.flush()
    elif template.role_pack != "it":
        raise ValueError(f"Template key {template_key!r} already belongs to another role pack")

    variants = [
        "Ticket {ticket_id} is currently {status}.",
        "The current status of ticket {ticket_id} is {status}.",
        "Here is the latest status for {ticket_id}: {status}.",
        "Support ticket {ticket_id} has the status: {status}.",
        "Your ticket {ticket_id} is marked as {status}.",
    ]
    for variant_text in variants:
        result = await session.execute(
            select(ResponseVariant).where(
                ResponseVariant.template_id == template.template_id,
                ResponseVariant.variant_text == variant_text,
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(ResponseVariant(template_id=template.template_id, variant_text=variant_text))

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

ADMISSIONS_FEE_DEADLINE_PHRASES = [
    "when is the last date to pay fees?",
    "what are the admission deadlines?",
    "how much is the tuition fee for B.Tech?",
    "what is the last date to submit the application?",
    "admission fee structure and payment dates",
    "when does the merit list come out?",
    "what is the refund policy for admission fees?",
    "when is the document verification deadline?",
    "tuition fee for MBA program",
    "what is the application fee?",
    "how much is the hostel fee?",
    "tuition fee for Data Science MTech",
    "what are the fee deadlines?",
    "last date for admission application",
    "important dates and fees for admission",
    "what is the fee refund policy?",
    "when do classes commence?",
    "orientation date and admission timeline",
    "what is the second merit list deadline?",
    "how much is the caution deposit?",
]

ADMISSIONS_FEE_DEADLINE_VARIANTS = [
    "According to the {academic_year} admissions calendar: {details}",
    "For the {academic_year} academic year: {details}",
    "Here are the admissions calendar details ({academic_year}): {details}",
    "Based on the official {academic_year} admissions calendar: {details}",
    "Per the {academic_year} admissions schedule: {details}",
]

async def seed_admissions_data(session: AsyncSession):
    """Seed Admissions role-pack intents, phrases, and response templates (slice-22, slice-25, slice-26)."""
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

    # 3. Intent: ask_fee_deadline (slice-26)
    stmt_fee = select(Intent).where(Intent.name == "ask_fee_deadline")
    res_fee = await session.execute(stmt_fee)
    fee_intent = res_fee.scalar_one_or_none()
    if not fee_intent:
        fee_intent = Intent(
            role_pack="admissions",
            name="ask_fee_deadline",
            intent_type="dynamic_workflow",
            needs_retrain=False,
        )
        session.add(fee_intent)
        await session.flush()
        logger.info("Created intent: ask_fee_deadline")
    else:
        fee_intent.intent_type = "dynamic_workflow"

    # Seed training phrases for ask_fee_deadline
    for phrase_text in ADMISSIONS_FEE_DEADLINE_PHRASES:
        phrase_stmt = select(TrainingPhrase).where(
            TrainingPhrase.intent_id == fee_intent.intent_id,
            TrainingPhrase.phrase_text == phrase_text,
        )
        existing = await session.execute(phrase_stmt)
        if not existing.scalar_one_or_none():
            session.add(TrainingPhrase(intent_id=fee_intent.intent_id, phrase_text=phrase_text))

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

    # 8. Response Template: ask_fee_deadline_response + 5 variants (slice-26)
    stmt_tmpl_fee = select(ResponseTemplate).where(
        ResponseTemplate.template_key == "ask_fee_deadline_response"
    )
    res_tmpl_fee = await session.execute(stmt_tmpl_fee)
    tmpl_fee = res_tmpl_fee.scalar_one_or_none()
    if not tmpl_fee:
        tmpl_fee = ResponseTemplate(
            role_pack="admissions",
            template_key="ask_fee_deadline_response",
            base_text="According to the {academic_year} admissions calendar: {details}",
            allow_rephrasing=True,
            available_variables=["academic_year", "details"],
        )
        session.add(tmpl_fee)
        await session.flush()
        logger.info("Created response template: ask_fee_deadline_response")

    for var_text in ADMISSIONS_FEE_DEADLINE_VARIANTS:
        stmt_var_fee = select(ResponseVariant).where(
            ResponseVariant.template_id == tmpl_fee.template_id,
            ResponseVariant.variant_text == var_text,
        )
        existing_var_fee = (await session.execute(stmt_var_fee)).scalar_one_or_none()
        if not existing_var_fee:
            session.add(ResponseVariant(template_id=tmpl_fee.template_id, variant_text=var_text))

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
