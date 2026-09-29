# VARIO UI Implementation Specification

**Status:** FROZEN FOR FRONTEND IMPLEMENTATION  
**Scope:** VARIO v1 Next.js frontend  
**Source package:** the 10 HTML mockups in this directory

This document is the implementation contract for the mockups. The HTML files are the visual/state reference; this document defines the shared behavior and component boundaries that should be preserved when translating them into Next.js/React.

## 1. Canonical page map

| Mockup | Recommended route | Purpose |
|---|---|---|
| `01-login.html` | `/login` | Delegated authentication entry |
| `02-home.html` | `/` | Conversation list / landing page |
| `03-new-conversation.html` | `/conversations/new` | Role-pack selection |
| `04-chat-view.html` | `/conversations/:conversationId` | Text conversation and workflow interaction |
| `05-talk-mode.html` | `/conversations/:conversationId/talk` | Voice interaction over the same conversation flow |
| `06-admin-intent-list.html` | `/admin/intents` | Intent/FAQ inventory |
| `07-admin-create-edit-intent.html` | `/admin/intents/new` and `/admin/intents/:intentId/edit` | Intent configuration |
| `08-admin-retraining.html` | `/admin/retraining` | Retraining status and trigger |
| `09-admin-audit-log.html` | `/admin/audit-log` | Audit events |
| `10-admin-conversation-logs.html` | `/admin/conversation-logs` | Operational conversation logs |

Routes are a frontend reference. Keep the actual API paths defined by the VARIO backend contract; do not move business logic into the browser.

## 2. State contract

| View | Required states | Expected behavior |
|---|---|---|
| Login | `default`, `loading`, `error` | Loading disables submission; error remains recoverable without losing entered credentials. |
| Home | `loaded`, `empty`, `loading` | Empty state offers New Conversation; loading preserves shell/context. |
| New Conversation | selection | Selecting HR/IT/Admissions establishes the role-pack context before chat creation. |
| Chat | `active`, `loading`, `empty`, `error` | Never silently discard user input; retry preserves conversation context. |
| Talk | `idle`, `listening`, `processing`, `unavailable` | Voice failure always exposes text fallback. |
| Intent List | `loaded`, `loading`, `empty`, `error` | CRUD actions are role-authorized; errors are recoverable. |
| Intent Editor | `workflow`, `faq` | Workflow/FAQ changes the relevant fields and validation rules. |
| Retraining | `uptodate`, `needed`, `complete`, `failed` | Retraining is explicit; progress/result is visible; failure is retryable. |
| Audit Log | `loaded`, `loading`, `empty`, `error` | Read-only operational history. |
| Conversation Logs | `loaded`, `loading`, `empty`, `error` | Read-only operational history with privacy-conscious display. |

The state selector shown in mockups is a development-review control only. It must not exist in production UI.

## 3. Shared application shell

Implement a reusable shell rather than duplicating page chrome.

### End-user shell
- VARIO brand/header
- Conversation navigation
- New Conversation action
- Active role-pack context
- Current user/session context
- Main content region
- Responsive mobile navigation

### Admin shell
- Admin navigation
- Active section
- Role/authorization context
- Main content region
- Consistent table/filter/action patterns

Suggested React components:

```text
AppShell
├── Sidebar / MobileNav
├── TopBar
├── RoleContext
├── UserMenu
└── PageContent
```

## 4. Shared component contract

The following should become reusable components rather than page-specific copies:

```text
Button
IconButton
Input
Textarea
Select
Badge
StatusBadge
RoleBadge
RoleSelector
Avatar
Card / Panel
EmptyState
LoadingState
ErrorState
ConfirmationDialog
Toast / InlineAlert
ConversationCard
ChatMessage
ChatComposer
WorkflowSummary
VoiceControl
DataTable
FilterBar
Pagination
AuditEvent
IntentTypeToggle
TrainingPhraseList
ResponseTemplateEditor
RetrainingStatus
```

## 5. Role context

VARIO has three role packs in v1:

- **HR** — leave, policy FAQ, leave request
- **IT Support** — ticket creation/status, password reset
- **Admissions** — application status, documents, fees/deadlines

Role selection must be visible in the UI and must not be treated as a purely cosmetic theme. The selected role determines the active role-pack context sent through the existing conversation flow.

Use the role accents from the mockups consistently, but do not duplicate role-routing logic in the frontend.

## 6. Workflow safety

Any record-affecting workflow must use a confirmation step before the mutation is submitted.

Required pattern:

```text
User request
  -> collect/validate fields
  -> show proposed operation
  -> Confirm / Cancel
  -> only Confirm submits mutation
  -> show result/reference ID
```

Examples include leave requests and IT ticket creation. The frontend must not infer success before the backend confirms it.

## 7. Chat behavior

The chat screen is the primary integration surface.

Required behavior:

- Maintain conversation ID/context.
- Show user and assistant messages distinctly.
- Show loading/processing without replacing existing messages.
- Preserve user input when a request fails.
- Provide retry for recoverable failures.
- Surface clarification when the backend/router requests it.
- Surface workflow confirmation before record-affecting actions.
- Allow transition to Talk Mode without creating a separate conversation context.

## 8. Talk Mode behavior

Talk Mode is another presentation of the same conversation flow, not a separate assistant.

```text
idle
  -> listening
  -> processing
  -> assistant response
  -> idle
```

If browser speech recognition or audio playback is unavailable/fails:

```text
unavailable
  -> show clear reason
  -> offer text-chat fallback
```

Do not make voice availability a hard dependency for text chat.

## 9. Admin intent lifecycle

The UI should represent this lifecycle clearly:

```text
Intent
  -> Training Phrases
  -> Response Template
  -> Generated Variants
  -> Admin Review
  -> needs_retrain=true
  -> Retrain
  -> Live role-pack reload
  -> retraining flag cleared
```

`dynamic_workflow` and `static_faq` are functional intent types from the VARIO contract. The frontend should expose the appropriate configuration fields for each type without implementing Rasa training logic itself.

## 10. Data and API boundary

The mockups are not a replacement for the backend contract.

The Next.js frontend should call the existing VARIO gateway/backend APIs for:

- authentication
- conversations
- chat
- admin intents
- training phrases / variants
- response templates
- retraining
- conversation logs
- audit logs

Do not place database access, Rasa calls, secrets, or provider credentials in browser code.

## 11. Accessibility and responsive requirements

Implementation must preserve:

- visible keyboard focus
- semantic buttons/links/forms
- accessible labels for icon-only controls
- disabled states for unavailable actions
- inline validation/error messaging
- sufficient text contrast
- keyboard-operable dialogs and menus
- responsive layouts for desktop, tablet and mobile
- usable Talk Mode controls on narrow screens

## 12. Security/privacy UI requirements

- Admin pages must respect the authenticated role/authorization supplied by the backend.
- Never expose JWTs, provider credentials, database credentials, or secrets in UI state/logs.
- Minimize unnecessary PII in conversation/audit displays.
- Treat audit and conversation logs as sensitive operational data.
- Do not let the frontend bypass backend authorization by hiding controls alone.

## 13. What is intentionally NOT part of this frozen UI

Do not add new v1 product surfaces for:

- advanced analytics
- proactive notifications
- native mobile applications
- multi-language support
- real enterprise integrations
- full user-management administration

Those remain outside the current VARIO v1 scope unless the repository requirements are formally changed.

## 14. Implementation rule

Use these files as the visual/state reference while implementing the actual Next.js components. Prefer shared components and small page-level compositions over copying the HTML/CSS into production.

If an implementation decision conflicts with the repository's API contract, security rules, or `AGENTS.md`, the repository requirements take precedence and the discrepancy should be documented for review.
