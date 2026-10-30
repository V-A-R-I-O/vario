"""Provider-agnostic rephraser service (slice-09).

Supports:
1. Response variant generation: on template save (allow_rephrasing=True),
   generates up to 4 paraphrased variants of base_text preserving placeholders.
   Returns [base_text] + valid_variants (original at index 0).
2. Training phrase generation: on demand ("Generate Similar"), generates ~8
   similar training phrases seeded from existing ones for admin review.

Provider selection via REPHRASER_PROVIDER (default: "gemini").
Key read from GEMINI_API_KEY via environment/config, never hardcoded.
"""
import json
import logging
import os
import re
from typing import List, Optional, Protocol, Sequence

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _placeholders(text: str) -> set:
    return set(_PLACEHOLDER_RE.findall(text or ""))


class RephraserClient(Protocol):
    """Contract for swappable rephraser providers."""

    async def generate_variants(
        self, base_text: str, available_variables: Sequence[str]
    ) -> List[str]:
        """Return the response variants for a template.

        The first element is always the original `base_text`; any further
        elements are generated paraphrases (placeholders preserved).
        """
        ...

    async def generate_phrases(
        self, seed_phrases: Sequence[str], count: int = 8
    ) -> List[str]:
        """Return `count` training-phrase variants seeded from existing phrases."""
        ...


class PassthroughRephraser:
    """Default no-op client: stores the original, generates nothing."""

    async def generate_variants(
        self, base_text: str, available_variables: Sequence[str]
    ) -> List[str]:
        return [base_text]

    async def generate_phrases(
        self, seed_phrases: Sequence[str], count: int = 8
    ) -> List[str]:
        return []
