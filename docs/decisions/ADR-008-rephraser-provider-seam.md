# ADR-008: Provider-Agnostic Rephraser Service with Gemini

## Context
Admins configure static FAQs and edit response templates for dynamic workflows. To ensure the assistant does not repeat answers verbatim, templates with `allow_rephrasing: true` require paraphrased response variants, and training phrase authoring benefits from "Generate Similar" recommendations.

## Decision
1. **Interface Contract:** Defined `RephraserClient` Protocol with `generate_variants` and `generate_phrases`.
2. **Provider Selection:** Controlled via `REPHRASER_PROVIDER` (default `gemini`, fallback `passthrough`), read dynamically at runtime so provider swaps require zero code changes.
3. **Gemini Implementation:** Uses Google AI Studio Gemini API (`gemini-1.5-flash`) over asynchronous `httpx`, avoiding heavy SDK overhead while leveraging JSON schema generation for structured output.
4. **Placeholder Validation:** Placeholders (e.g. `{balance}`, `{ticket_id}`) are strictly extracted and verified against `base_text`. Any LLM-generated variant that drops, alters, or adds placeholders is rejected and excluded from persistence.
5. **Graceful Degradation:** If the LLM call times out, returns HTTP errors, or has no API key configured, the service logs the event and falls back to preserving the original base text as variant 0 without crashing the admin workflow.
6. **Secrets Handling:** `GEMINI_API_KEY` is loaded from environment / configuration and is never hardcoded, logged, or serialized.

## Status
Accepted (Sprint 4, Slice 09).
