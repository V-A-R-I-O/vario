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


class GeminiRephraser:
    """Gemini API provider for variant and phrase generation via Google AI Studio."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._api_key = api_key
        self._model = model
        self._http_client = http_client

    @property
    def api_key(self) -> str:
        return (
            self._api_key
            or os.getenv("GEMINI_API_KEY")
            or getattr(settings, "GEMINI_API_KEY", "")
        )

    @property
    def model(self) -> str:
        return (
            self._model
            or os.getenv("GEMINI_MODEL")
            or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        )

    def _get_url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    async def _call_gemini(self, prompt: str) -> Optional[str]:
        key = self.api_key
        if not key:
            logger.warning("GEMINI_API_KEY is not configured; skipping Gemini call.")
            return None

        url = self._get_url()
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "response_mime_type": "application/json",
            },
        }

        try:
            if self._http_client:
                resp = await self._http_client.post(url, json=payload, timeout=10.0)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)

            if resp.status_code != 200:
                logger.error(
                    "Gemini API returned status %s: %s", resp.status_code, resp.text
                )
                return None

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("Gemini API returned no candidates.")
                return None

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                logger.warning("Gemini API candidate has no parts.")
                return None

            return parts[0].get("text", "")
        except Exception as exc:
            logger.error("Gemini API request failed: %s", exc)
            return None

    def _parse_json_list(self, raw_text: str) -> List[str]:
        if not raw_text:
            return []
        cleaned = raw_text.strip()
        # Strip markdown code blocks if present
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            if isinstance(parsed, dict):
                for key in ["variants", "phrases", "paraphrases", "data", "results"]:
                    val = parsed.get(key)
                    if isinstance(val, list):
                        return [str(item).strip() for item in val if str(item).strip()]
        except json.JSONDecodeError:
            pass

        # Fallback line-by-line parsing
        results = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r'^(?:[-*]|\d+[\.)])\s*', '', line).strip(' "[],\'')
            if line:
                results.append(line)
        return results

    async def generate_variants(
        self, base_text: str, available_variables: Sequence[str]
    ) -> List[str]:
        """Generate up to 4 paraphrased variants of base_text preserving placeholders.

        Returns [base_text] at index 0 followed by up to 4 valid paraphrases.
        Any variant with missing, altered, or extra placeholders is dropped.
        """
        if not base_text or not base_text.strip():
            return [base_text]

        required = _placeholders(base_text)
        if required:
            var_list = ", ".join(f"{{{v}}}" for v in sorted(required))
            prompt = (
                f"You are a conversational assistant response rephraser.\n"
                f"Generate exactly 4 distinct paraphrased variations of the following text:\n"
                f'\"{base_text}\"\n\n'
                f"CRITICAL REQUIREMENT:\n"
                f"The following placeholder(s) MUST appear in EVERY variation exactly as written with curly braces:\n"
                f"{var_list}\n"
                f"Do NOT invent, alter, or remove any placeholders.\n"
                f"Keep the meaning identical and natural.\n"
                f'Return ONLY a JSON array of 4 strings, e.g. [\"variant 1\", \"variant 2\", \"variant 3\", \"variant 4\"].'
            )
        else:
            prompt = (
                f"You are a conversational assistant response rephraser.\n"
                f"Generate exactly 4 distinct paraphrased variations of the following text:\n"
                f'\"{base_text}\"\n\n'
                f"CRITICAL REQUIREMENT:\n"
                f"Do NOT include any placeholders or curly braces like {{var}} in the output.\n"
                f"Keep the meaning identical and natural.\n"
                f'Return ONLY a JSON array of 4 strings, e.g. [\"variant 1\", \"variant 2\", \"variant 3\", \"variant 4\"].'
            )

        raw = await self._call_gemini(prompt)
        if not raw:
            return [base_text]

        candidates = self._parse_json_list(raw)
        valid_variants: List[str] = []
        seen = {base_text.strip()}

        for text in candidates:
            cleaned = text.strip()
            if not cleaned or cleaned in seen:
                continue
            # Validate placeholders: must match required set exactly
            if _placeholders(cleaned) != required:
                logger.warning(
                    "Dropping variant due to placeholder mismatch: %r (required: %r, found: %r)",
                    cleaned,
                    required,
                    _placeholders(cleaned),
                )
                continue
            seen.add(cleaned)
            valid_variants.append(cleaned)
            if len(valid_variants) == 4:
                break

        return [base_text] + valid_variants

    async def generate_phrases(
        self, seed_phrases: Sequence[str], count: int = 8
    ) -> List[str]:
        """Generate training phrases seeded from existing ones."""
        if not seed_phrases:
            return []

        seeds_formatted = "\n".join(f"- {p}" for p in seed_phrases)
        prompt = (
            f"You are an NLU training phrase generator for an enterprise assistant.\n"
            f"Given these seed phrases for an intent:\n"
            f"{seeds_formatted}\n\n"
            f"Generate exactly {count} diverse, realistic training phrases that users might say with the same intent.\n"
            f"Vary syntax, vocabulary, and formality. Do not repeat the seed phrases.\n"
            f'Return ONLY a JSON array of {count} strings, e.g. [\"phrase 1\", \"phrase 2\", ...].'
        )

        raw = await self._call_gemini(prompt)
        if not raw:
            return []

        candidates = self._parse_json_list(raw)
        seed_set = {p.strip().lower() for p in seed_phrases}
        valid: List[str] = []
        seen = set()

        for phrase in candidates:
            cleaned = phrase.strip()
            if not cleaned:
                continue
            lower = cleaned.lower()
            if lower in seed_set or lower in seen:
                continue
            seen.add(lower)
            valid.append(cleaned)
            if len(valid) == count:
                break

        return valid
