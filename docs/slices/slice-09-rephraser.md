# Slice 09 — rephraser

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** A · **Sprint:** 4 · **Module:** `rephraser-service`

## References — read these first
- `AGENTS.md` (human review required — wires the Gemini API key)
- `docs/api-contract.md` § Admin — Intents (`POST` returns original + 4 variants), § Response Templates (`PUT` regenerates 4), § Training Phrase Generation (`POST /api/admin/intents/:id/generate-phrases`)
- `docs/ADD.md` → `rephraser-service` module (provider-agnostic; the two functions; placeholder preservation/validation) + admin flow diagram
- `docs/ui-reference.md` § 7 → "Generate Similar" (accept/edit/reject/accept-all) + variant section
- `docs/vario-overview.md` § 6 — US-8, US-9
- `slice-08-admin-intent-crud` (the `RephraserClient` seam this replaces)
- `.env.example` (`REPHRASER_PROVIDER`, `GEMINI_API_KEY`)

## What to build
The provider-agnostic rephraser behind the `RephraserClient` interface `slice-08` stubbed. Two functions: response-variant generation (on template save) and training-phrase generation (on demand). Default provider Gemini, selectable via `REPHRASER_PROVIDER`.

Deliverables:
- **Provider-agnostic service** behind a swappable interface; provider chosen via `REPHRASER_PROVIDER` (default `gemini`, key `GEMINI_API_KEY`). Replaces the passthrough default from `slice-08`.
- **Response-variant generation** — on `POST /api/admin/intents` and `PUT /api/admin/templates/:id` (when `allow_rephrasing`), send `base_text` to the LLM asking for 4 paraphrases; **preserve and validate placeholders** (drop any variant that lost/altered a placeholder); store the original (index 0) + up to 4 valid variants. Synchronous (~3–5s).
- **Training-phrase generation** — `POST /api/admin/intents/:id/generate-phrases` uses existing phrases as seed, returns ~8 (default) phrases for review. **Not auto-saved** — the UI reviews/accepts, then persists accepted ones via `PUT /api/admin/intents/:id`.
- **UI wiring** — the Generate-Similar review list (accept / edit / reject / accept-all) and the variant editor from `slice-08`'s shell, now backed by real generation.
- **Graceful failure** — if the LLM call fails/times out, keep the original variant and surface a clear error rather than blocking the save.

## Acceptance criteria
- [ ] Given a template save with `allow_rephrasing`, then the response contains the original plus up to 4 generated variants, all preserving the base placeholders (US-9).
- [ ] Given a variant the LLM returned with a dropped/renamed placeholder, then it is rejected and not stored.
- [ ] Given `PUT /api/admin/templates/:id`, then old variants are replaced with newly generated ones.
- [ ] Given `POST /api/admin/intents/:id/generate-phrases`, then ~8 seed-based phrases are returned and **not** auto-saved (US-8); with no seed phrases, then `422`.
- [ ] Given accepted phrases, when saved via `PUT /api/admin/intents/:id` (`training_phrases.add`), then they persist.
- [ ] Given `REPHRASER_PROVIDER`, then the provider is selected via env with no code change; the key is read from env, never hardcoded.
- [ ] Given an LLM failure, then the save keeps the original variant and reports the error (no crash).

## Mockup / reference (if UI-facing)
`docs/design/admin-create-edit-intent.html` — Generate-Similar + variant sections (matches `docs/ui-reference.md` §7).

## Out of scope for this slice
- Retraining (`slice-10`) — generating variants/phrases only flags `needs_retrain`; it does not retrain.
- Deep implementation of non-Gemini providers (ship the interface + Gemini; others are pluggable later).

## Human review required?
**Yes** — wires the Gemini API key (a secret). Review the credential/env handling (per `AGENTS.md`).
