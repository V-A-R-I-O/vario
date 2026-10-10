"""response-renderer — pick a stored variant and substitute slot values.

Given a `template_key` and slot values, selects a *random* variant from
`response_variants` for that template and substitutes `{placeholder}` tokens
(ADD §response-renderer). Pure DB read + string substitution.
"""
import logging
import random
import string
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant

logger = logging.getLogger("vario.response_renderer")


class _SafeDict(dict):
    """Leave unknown `{placeholders}` untouched instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _substitute(text: str, slots: Dict[str, Any]) -> str:
    values = _SafeDict({k: ("" if v is None else v) for k, v in (slots or {}).items()})
    try:
        return string.Formatter().vformat(text, (), values)
    except (ValueError, IndexError):
        # Malformed template braces — return the raw text rather than 500.
        return text


async def render(
    db: AsyncSession,
    template_key: str,
    slots: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Return a rendered response for `template_key`, or None if it has no variants."""
    result = await db.execute(
        select(ResponseVariant)
        .join(ResponseTemplate, ResponseVariant.template_id == ResponseTemplate.template_id)
        .where(ResponseTemplate.template_key == template_key)
    )
    variants = result.scalars().all()

    if not variants:
        logger.warning("no variants found for template_key=%s", template_key)
        return None

    chosen = random.choice(variants)
    return _substitute(chosen.variant_text, slots or {})
