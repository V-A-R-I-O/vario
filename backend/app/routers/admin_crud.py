"""admin-crud (slice-08) — intents, response templates, and variants.

Full CRUD for the admin's role-pack config, scoped by the slice-07 admin guard.
Enforces the rules that keep developer-owned dynamic workflows safe while letting
admins own their static FAQs:

- FAQ create → `static_faq`, empty `available_variables`, `needs_retrain=true`.
- Renaming a `dynamic_workflow` → 403 (name is immutable); only FAQs rename.
- Delete → `static_faq` only (dynamic → 403); cascades phrases/template/variants.
- Variant edit → 422 if it drops a placeholder the base template requires.
- Variant delete → 400 on the original (position 0).
- Any op on another role pack's resource → 403.

Variant generation / "Generate Similar" go through the rephraser seam
(`services.rephraser.client`), which is a passthrough until slice-09.
"""
import logging
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.intent import Intent
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from app.models.training_phrase import TrainingPhrase
from app.schemas.admin import (
    GeneratePhrasesRequest,
    GeneratePhrasesResponse,
    IntentCreate,
    IntentDeleteResponse,
    IntentListResponse,
    IntentOut,
    IntentResponse,
    IntentUpdate,
    IntentUpdateOut,
    IntentUpdateResponse,
    PhraseOut,
    TemplateListResponse,
    TemplateOut,
    TemplateResponse,
    TemplateUpdate,
    VariantDeleteResponse,
    VariantOut,
    VariantResponse,
    VariantUpdate,
)
from app.services import rephraser, audit_log_service
from app.services.admin_guard import AdminContext, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

DYNAMIC = "dynamic_workflow"
STATIC = "static_faq"
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _template_key(name: str) -> str:
    return f"{name}_response"


def _placeholders(text: str) -> set:
    return set(_PLACEHOLDER_RE.findall(text or ""))


# --- loaders (scoping + 404/403) -------------------------------------------


async def _get_intent(db: AsyncSession, intent_id: str, admin: AdminContext) -> Intent:
    result = await db.execute(select(Intent).where(Intent.intent_id == intent_id))
    intent = result.scalars().first()
    if not intent:
        raise HTTPException(status_code=404, detail="Intent not found")
    if intent.role_pack != admin.role_pack:
        raise HTTPException(status_code=403, detail="Intent belongs to another role pack")
    return intent


async def _get_template_for_intent(db: AsyncSession, intent: Intent) -> Optional[ResponseTemplate]:
    result = await db.execute(
        select(ResponseTemplate).where(
            ResponseTemplate.template_key == _template_key(intent.name),
            ResponseTemplate.role_pack == intent.role_pack,
        )
    )
    return result.scalars().first()


async def _phrases_for(db: AsyncSession, intent_id: str) -> List[TrainingPhrase]:
    result = await db.execute(
        select(TrainingPhrase)
        .where(TrainingPhrase.intent_id == intent_id)
        .order_by(TrainingPhrase.created_at)
    )
    return list(result.scalars().all())


async def _variants_for(db: AsyncSession, template_id: str) -> List[ResponseVariant]:
    result = await db.execute(
        select(ResponseVariant)
        .where(ResponseVariant.template_id == template_id)
        .order_by(ResponseVariant.position)
    )
    return list(result.scalars().all())


# --- serializers ------------------------------------------------------------


def _variant_out(v: ResponseVariant) -> VariantOut:
    return VariantOut(id=v.variant_id, variant_text=v.variant_text, generated_at=v.generated_at)


async def _template_out(db: AsyncSession, template: ResponseTemplate) -> TemplateOut:
    variants = await _variants_for(db, template.template_id)
    return TemplateOut(
        id=template.template_id,
        template_key=template.template_key,
        base_text=template.base_text,
        allow_rephrasing=bool(template.allow_rephrasing),
        available_variables=list(template.available_variables or []),
        variants=[_variant_out(v) for v in variants],
    )


async def _intent_out(db: AsyncSession, intent: Intent) -> IntentOut:
    phrases = await _phrases_for(db, intent.intent_id)
    template = await _get_template_for_intent(db, intent)
    return IntentOut(
        id=intent.intent_id,
        name=intent.name,
        role_pack=intent.role_pack,
        intent_type=intent.intent_type,
        needs_retrain=bool(intent.needs_retrain),
        updated_at=intent.updated_at,
        training_phrases=[PhraseOut(id=p.phrase_id, phrase_text=p.phrase_text) for p in phrases],
        response_template=(await _template_out(db, template)) if template else None,
    )


async def _create_variants(db: AsyncSession, template: ResponseTemplate) -> None:
    """(Re)create variants for a template via the rephraser seam, position-ordered."""
    if not template.allow_rephrasing:
        texts = [template.base_text]
    else:
        try:
            texts = await rephraser.client.generate_variants(
                template.base_text, list(template.available_variables or [])
            )
            if not texts:
                texts = [template.base_text]
        except Exception as e:
            logger.error(f"Rephraser variant generation failed: {e}")
            texts = [template.base_text]

    for i, text in enumerate(texts):
        db.add(ResponseVariant(template_id=template.template_id, variant_text=text, position=i))


# --- Intents ----------------------------------------------------------------


@router.get("/intents", response_model=IntentListResponse)
async def list_intents(
    needs_retrain: Optional[bool] = None,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Intent).where(Intent.role_pack == admin.role_pack)
    if needs_retrain is not None:
        stmt = stmt.where(Intent.needs_retrain == needs_retrain)
    stmt = stmt.order_by(Intent.name)
    result = await db.execute(stmt)
    intents = result.scalars().all()
    return IntentListResponse(
        role_pack=admin.role_pack,
        intents=[await _intent_out(db, i) for i in intents],
    )


@router.post("/intents", response_model=IntentResponse, status_code=201)
async def create_intent(
    payload: IntentCreate,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    phrases = [p.strip() for p in payload.training_phrases if p and p.strip()]
    if not phrases:
        raise HTTPException(status_code=422, detail="At least one training phrase is required")

    # Duplicate-name guard (name is globally unique in the schema).
    existing = await db.execute(select(Intent).where(Intent.name == payload.name))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Intent name already exists for this role pack")

    # Admins only ever create static FAQs with no variables.
    intent = Intent(
        role_pack=admin.role_pack,
        name=payload.name,
        intent_type=STATIC,
        needs_retrain=True,
    )
    db.add(intent)

    for text in phrases:
        db.add(TrainingPhrase(intent=intent, phrase_text=text, author_id=admin.user_id))

    template = ResponseTemplate(
        role_pack=admin.role_pack,
        template_key=_template_key(payload.name),
        base_text=payload.response_template.base_text,
        allow_rephrasing=payload.response_template.allow_rephrasing,
        available_variables=[],
    )
    db.add(template)
    await db.flush()
    await _create_variants(db, template)

    await db.commit()
    await db.refresh(intent)

    await audit_log_service.record(
        db,
        actor_id=admin.user_id,
        role_pack=admin.role_pack,
        action_type="intent_created",
        reference_id=intent.intent_id,
        details={"name": intent.name, "intent_type": intent.intent_type},
    )

    return IntentResponse(intent=await _intent_out(db, intent))


@router.put("/intents/{intent_id}", response_model=IntentUpdateResponse)
async def update_intent(
    intent_id: str,
    payload: IntentUpdate,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    intent = await _get_intent(db, intent_id, admin)

    if payload.name is not None and payload.name != intent.name:
        # Dynamic workflow names are developer-owned and immutable.
        if intent.intent_type == DYNAMIC:
            raise HTTPException(status_code=403, detail="Cannot rename a dynamic workflow intent")
        dupe = await db.execute(
            select(Intent).where(Intent.name == payload.name, Intent.intent_id != intent_id)
        )
        if dupe.scalars().first():
            raise HTTPException(status_code=409, detail="New name already exists for this role pack")
        # Keep the template_key in sync with the (FAQ) intent name.
        template = await _get_template_for_intent(db, intent)
        if template:
            template.template_key = _template_key(payload.name)
        intent.name = payload.name

    if payload.training_phrases is not None:
        for rid in payload.training_phrases.remove:
            row = await db.execute(
                select(TrainingPhrase).where(
                    TrainingPhrase.phrase_id == rid, TrainingPhrase.intent_id == intent_id
                )
            )
            phrase = row.scalars().first()
            if phrase:
                await db.delete(phrase)
        for text in payload.training_phrases.add:
            cleaned = text.strip()
            if cleaned:
                db.add(TrainingPhrase(intent_id=intent_id, phrase_text=cleaned, author_id=admin.user_id))

    intent.needs_retrain = True
    await db.commit()
    await db.refresh(intent)

    await audit_log_service.record(
        db,
        actor_id=admin.user_id,
        role_pack=admin.role_pack,
        action_type="intent_updated",
        reference_id=intent.intent_id,
        details={"name": intent.name},
    )

    phrases = await _phrases_for(db, intent_id)
    return IntentUpdateResponse(
        intent=IntentUpdateOut(
            id=intent.intent_id,
            name=intent.name,
            needs_retrain=bool(intent.needs_retrain),
            training_phrases=[PhraseOut(id=p.phrase_id, phrase_text=p.phrase_text) for p in phrases],
        )
    )


@router.delete("/intents/{intent_id}", response_model=IntentDeleteResponse)
async def delete_intent(
    intent_id: str,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    intent = await _get_intent(db, intent_id, admin)
    if intent.intent_type == DYNAMIC:
        raise HTTPException(status_code=403, detail="Dynamic workflows cannot be deleted")

    # Remove the template + its variants (sharing the key convention).
    template = await _get_template_for_intent(db, intent)
    if template:
        for v in await _variants_for(db, template.template_id):
            await db.delete(v)
        await db.delete(template)

    intent_name = intent.name
    # Intent cascade removes its training phrases.
    await db.delete(intent)
    await db.commit()

    await audit_log_service.record(
        db,
        actor_id=admin.user_id,
        role_pack=admin.role_pack,
        action_type="intent_deleted",
        reference_id=intent_id,
        details={"name": intent_name},
    )

    return IntentDeleteResponse(deleted_intent_id=intent_id, needs_retrain=True)


@router.post("/intents/{intent_id}/generate-phrases", response_model=GeneratePhrasesResponse)
async def generate_phrases(
    intent_id: str,
    payload: GeneratePhrasesRequest = GeneratePhrasesRequest(),
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    intent = await _get_intent(db, intent_id, admin)
    phrases = await _phrases_for(db, intent_id)
    if not phrases:
        raise HTTPException(status_code=422, detail="Intent has no training phrases to seed generation")

    # Rephraser seam: passthrough returns [] until slice-09 wires real generation.
    generated = await rephraser.client.generate_phrases(
        [p.phrase_text for p in phrases], payload.count
    )
    return GeneratePhrasesResponse(intent_id=intent_id, generated_phrases=generated)


# --- Templates --------------------------------------------------------------


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResponseTemplate)
        .where(ResponseTemplate.role_pack == admin.role_pack)
        .order_by(ResponseTemplate.template_key)
    )
    templates = result.scalars().all()
    return TemplateListResponse(
        role_pack=admin.role_pack,
        templates=[await _template_out(db, t) for t in templates],
    )


@router.put("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    payload: TemplateUpdate,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResponseTemplate).where(ResponseTemplate.template_id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.role_pack != admin.role_pack:
        raise HTTPException(status_code=403, detail="Template belongs to another role pack")

    base_text_changed = payload.base_text is not None and payload.base_text != template.base_text

    if payload.allow_rephrasing is not None:
        template.allow_rephrasing = payload.allow_rephrasing
    if payload.base_text is not None:
        template.base_text = payload.base_text

    # Regenerate variants only when base_text changes (M9a)
    existing = await _variants_for(db, template_id)
    if base_text_changed:
        if template.allow_rephrasing:
            for v in existing:
                await db.delete(v)
            await db.flush()
            await _create_variants(db, template)
        else:
            for v in existing[1:]:
                await db.delete(v)
            if existing:
                existing[0].variant_text = template.base_text
            else:
                db.add(ResponseVariant(template_id=template_id, variant_text=template.base_text, position=0))

    await db.commit()
    await db.refresh(template)

    await audit_log_service.record(
        db,
        actor_id=admin.user_id,
        role_pack=admin.role_pack,
        action_type="template_edited",
        reference_id=template.template_id,
        details={"template_key": template.template_key},
    )

    return TemplateResponse(template=await _template_out(db, template))


# --- Variants ---------------------------------------------------------------


async def _get_variant_scoped(db: AsyncSession, variant_id: str, admin: AdminContext):
    result = await db.execute(select(ResponseVariant).where(ResponseVariant.variant_id == variant_id))
    variant = result.scalars().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    tpl_result = await db.execute(
        select(ResponseTemplate).where(ResponseTemplate.template_id == variant.template_id)
    )
    template = tpl_result.scalars().first()
    if not template or template.role_pack != admin.role_pack:
        raise HTTPException(status_code=403, detail="Variant belongs to another role pack")
    return variant, template


@router.put("/variants/{variant_id}", response_model=VariantResponse)
async def update_variant(
    variant_id: str,
    payload: VariantUpdate,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    variant, template = await _get_variant_scoped(db, variant_id, admin)

    # A variant must keep every placeholder the base template requires.
    required = _placeholders(template.base_text)
    present = _placeholders(payload.variant_text)
    missing = required - present
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Variant is missing required placeholder(s): {', '.join(sorted(missing))}",
        )

    variant.variant_text = payload.variant_text
    await db.commit()
    await db.refresh(variant)

    await audit_log_service.record(
        db,
        actor_id=admin.user_id,
        role_pack=admin.role_pack,
        action_type="variant_edited",
        reference_id=variant.variant_id,
        details={"template_id": template.template_id, "position": variant.position},
    )

    return VariantResponse(variant=_variant_out(variant))


@router.delete("/variants/{variant_id}", response_model=VariantDeleteResponse)
async def delete_variant(
    variant_id: str,
    admin: AdminContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    variant, _template = await _get_variant_scoped(db, variant_id, admin)
    if variant.position == 0:
        raise HTTPException(status_code=400, detail="Cannot delete the original base_text variant")
    template_id = _template.template_id
    pos = variant.position
    await db.delete(variant)
    await db.commit()

    await audit_log_service.record(
        db,
        actor_id=admin.user_id,
        role_pack=admin.role_pack,
        action_type="variant_deleted",
        reference_id=variant_id,
        details={"template_id": template_id, "position": pos},
    )

    return VariantDeleteResponse(deleted_variant_id=variant_id)
