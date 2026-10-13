"""Rephraser seam (slice-08).

`admin-crud` needs to generate response variants (on template save) and training
phrases (on "Generate Similar"), but the real LLM-backed rephraser is slice-09
(Sprint 4). This module defines the interface and ships a **passthrough default**
so CRUD works end-to-end now:

- `generate_variants` returns just the original base_text (variant index 0, no
  generated variants).
- `generate_phrases` returns an empty list (the route is wired; generation is
  stubbed until slice-09).

slice-09 implements a real client behind the same interface and swaps
`client` — no contract change for the CRUD routes.
"""
from typing import List, Protocol, Sequence


class RephraserClient(Protocol):
    """Contract both the passthrough and the real (slice-09) client satisfy."""

    async def generate_variants(self, base_text: str, available_variables: Sequence[str]) -> List[str]:
        """Return the response variants for a template.

        The first element is always the original `base_text`; any further
        elements are generated paraphrases (placeholders preserved).
        """
        ...

    async def generate_phrases(self, seed_phrases: Sequence[str], count: int) -> List[str]:
        """Return `count` training-phrase variants seeded from existing phrases."""
        ...


class PassthroughRephraser:
    """Default no-op client: stores the original, generates nothing."""

    async def generate_variants(self, base_text: str, available_variables: Sequence[str]) -> List[str]:
        return [base_text]

    async def generate_phrases(self, seed_phrases: Sequence[str], count: int) -> List[str]:
        return []


# The active client. slice-09 reassigns this to the real implementation.
client: RephraserClient = PassthroughRephraser()
