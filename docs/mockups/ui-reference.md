# V.A.R.I.O — UI Reference (for Mockups & Design Language)

> This doc tells the designer **what pages we need and what goes on each one**. It does NOT prescribe visual style — that's the designer's call.

---

## Page Inventory

| # | Page | Who sees it | Complexity |
|---|------|-------------|------------|
| 1 | Login | Everyone | Simple |
| 2 | Home / Conversation List | End users | Medium |
| 3 | New Conversation | End users | Simple |
| 4 | Chat View | End users | Complex |
| 5 | Talk Mode (overlay on Chat) | End users | Medium |
| 6 | Admin — Intent List | Role admins | Medium |
| 7 | Admin — Create/Edit Intent | Role admins | Complex |
| 8 | Admin — Retraining | Role admins | Simple |
| 9 | Admin — Audit Log | Role admins | Medium |
| 10 | Admin — Conversation Logs | Role admins | Medium |

**Total: 10 views** (5 end-user, 5 admin)

---

## Auth

### 1. Login Page

The only auth page. No registration, no forgot-password flow — VARIO delegates auth to the organization.

**Elements:**
- Email input field
- Password input field
- "Log in" button
- "Forgot your password? Contact your administrator." (plain text, not a link to a flow)
- VARIO logo / branding

**States:**
- Default (empty form)
- Loading (after submit, waiting for auth response)
- Error: "Invalid email or password" (the org's identity provider rejected the credentials)

> [!NOTE]
> No "account locked" state. VARIO delegates authentication to the organization's identity provider (see `docs/decisions/ADR-001-delegated-auth.md`) — lockout, retry throttling, and password policy all live in the org's IdP, not in VARIO.

---

## End User — Chat

### 2. Home / Conversation List

The landing page after login. Shows all past conversations.

**Elements:**
- **Left sidebar** (or full page on mobile):
  - List of past conversations, each showing:
    - Role pack icon/badge (HR / IT / Admissions)
    - Conversation title (auto-generated or user-provided)
    - Last message preview (truncated)
    - Timestamp ("2 hours ago", "Sep 7")
  - Sorted by most recent
  - Filter/group by role pack (optional)
- **"New Conversation" button** (prominent, always visible)
- **Empty state** when user has no conversations yet: illustration + "Start your first conversation" prompt

**States:**
- Conversations loaded (list populated)
- Empty (no conversations yet)
- Loading (fetching conversations)

---

### 3. New Conversation (modal or page)

User picks which department to talk to.

**Elements:**
- Three cards (one per role pack):
  - **HR** — icon, title, short description ("Leave balance, leave requests, HR policies")
  - **IT Support** — icon, title, description ("IT tickets, ticket status, password reset")
  - **Admissions** — icon, title, description ("Application status, document checklists, fee deadlines")
- Each card is clickable → starts a new conversation with that role pack

**Interaction:**
- Click card → conversation created → navigate to Chat View

---

### 4. Chat View

The main conversational interface. This is the most complex page.

**Layout:**
- **Left sidebar:** Conversation list (same as Home, but narrower — collapses on mobile)
- **Main area:**
  - **Header:** Role pack name + icon, conversation title
  - **Message thread** (scrollable):
    - User messages: right-aligned, distinct background
    - Bot messages: left-aligned, with bot avatar
  - **Input bar** at bottom: text input + send button + microphone toggle (for talk mode)

**Bot message types** (the designer needs to handle all of these):

| Type | What it looks like | Example |
|------|-------------------|---------|
| **Plain text** | Simple text bubble | "Hello! How can I help you today?" |
| **Data card** | Structured card with key-value pairs | Leave balance: 12 days (Casual: 5, Sick: 4, Earned: 3) |
| **Slot prompt** | Text + clickable option buttons | "What type of leave?" → [Casual] [Sick] [Earned] |
| **Confirmation** | Summary card + Confirm/Cancel buttons | "Casual leave, Sep 10–11, Family function" → [Confirm] [Cancel] |
| **Result** | Success card with reference ID | ✅ "Leave submitted! Ref: LEAVE-2045" |
| **Not found** | Warning-styled message with suggestion | ⚠️ "Application APP-9999 not found. Contact admissions@example.com" |
| **FAQ answer** | Longer text block, possibly with formatting | "Our WFH policy allows employees to work from home up to 3 days per week..." |
| **Error** | Error-styled message | ❌ "Something went wrong. Please try again." |
| **List** | Numbered or bulleted list | Document checklist: 1) 10th marksheet 2) 12th marksheet... |

**States:**
- Active conversation (messages flowing)
- Loading (bot is typing / thinking indicator)
- Empty conversation (just started, no messages yet — show a welcome prompt)
- Connection error

---

### 5. Talk Mode (overlay on Chat View)

Same chat view, but with voice controls overlaid. Not a separate page — a mode toggle.

**Additional elements:**
- **Microphone button** (replaces or sits beside send button):
  - Idle: microphone icon
  - Listening: pulsing/animated recording indicator + "Listening..."
  - Processing: "Processing..." while speech-to-text runs
- **Audio playback:** Bot responses auto-play as audio. Small speaker icon on bot messages to replay.
- **"Talk mode unavailable" banner** — shown when TTS credits are exhausted, with "Switch to text" action

**Interaction flow:**
1. User taps microphone → starts listening
2. User speaks → transcript appears in input bar in real-time
3. User stops → message sent automatically
4. Bot response appears as text + plays as audio
5. After audio finishes → auto-starts listening again (hands-free loop)

---

## Admin Console

Admins see a different navigation than end users. The admin console is scoped — an HR admin only sees HR data.

**Shared admin layout:**
- **Top bar:** Admin name, role badge (HR Admin / IT Admin / Admissions Admin), logout
- **Side navigation:** Intent Management, Retraining, Audit Log, Conversation Logs

---

### 6. Admin — Intent List

The main admin page. Shows all intents for this admin's role pack.

**Elements:**
- **Page header:** "HR Intents" (or IT / Admissions, depending on role)
- **"Add FAQ" button** (Creates a new static FAQ from scratch)
- **Retrain status banner:** "3 intents have changes. [Retrain now]" (shown when `needs_retrain` is true)
- **Intent table/list**, each row showing:
  - Intent name (e.g., `check_leave_balance` or `ask_wfh_policy`)
  - Type badge: `Dynamic Workflow` (pre-seeded by dev) vs `Static FAQ` (created by admin)
  - Number of training phrases
  - `Needs retrain` badge (if modified since last train)
  - Last updated timestamp
  - Actions: Edit, Delete (Delete is disabled for Dynamic Workflows)
- **Search/filter bar** (optional)

**States:**
- Intents loaded
- Empty (no intents configured yet — shouldn't happen with pre-seeded data, but handle it)
- After delete: confirmation dialog ("Delete intent 'ask_wfh_policy' and all its training data?")

---

### 7. Admin — Create/Edit Intent

The most complex admin page. This page has **two distinct modes** depending on whether the admin is editing a developer-created workflow or building a new FAQ.

#### Mode A: Editing a Pre-Seeded Dynamic Workflow
*These are intents like `check_ticket_status` that query an API. The admin cannot change the intent name or the variables, they only edit the English text.*

**Elements:**
- **System Key:** e.g., `ticket_status_response` (Read-only label).
- **Available Variables Panel:** A visual list of read-only badges/chips representing data the developer provides (e.g., `<badge>{ticket_id}</badge>`, `<badge>{status}</badge>`).
- **Response Template Textarea:** The admin types the text, injecting variables. e.g., `"Ticket {ticket_id} is currently {status}."`
- **Helper/Warning:** If the admin types `{ticket_status}` but only `{status}` is available, show a warning: *"Unknown variable `{ticket_status}`. Did you mean `{status}`?"*

#### Mode B: Creating a Static FAQ
*These are simple Q&A intents like `ask_wfh_policy` created entirely by the admin.*

**Elements:**
- **Intent Name:** Text input (e.g., `ask_wfh_policy`). Validated for no spaces/lowercase.
- **Response Template Textarea:** The admin types the answer. **No variables are allowed or shown** because no developer code is fetching data for it.

#### Shared Elements (Both Modes):
- **Training Phrases Section:**
  - List of current training phrases with delete ✕ buttons.
  - Text input to add a new phrase.
  - **"Generate Similar" button:**
    1. Click → loading spinner.
    2. Generated phrases appear in a reviewable list.
    3. ✅ Accept / ✏️ Edit / 🗑️ Reject buttons per phrase.
    4. "Accept All" bulk action.
- **Variant Generation Section:**
  - "Allow rephrasing" toggle (on/off).
  - When enabled and saved, 4 auto-generated paraphrased variants appear below.
  - Each variant is editable inline or deletable.
- **Footer:** "Save" button (sets `needs_retrain = true`) and "Cancel" button.

---

### 8. Admin — Retraining

Simple status page.

**Elements:**
- Role pack name ("HR Model")
- Last trained: timestamp
- Current status: "Up to date" / "X intents modified since last training"
- **"Retrain Now" button**
- After clicking:
  - Progress indicator: Pending → Training → Complete / Failed
  - Estimated time: "This may take 1–2 minutes"
  - On complete: success message + timestamp updated
  - On failure: error message with details

> [!NOTE]
> This could be a section on the Intent List page instead of a separate page — designer's call. The important thing is it's always accessible and shows retrain status prominently.

---

### 9. Admin — Audit Log

Filterable table of business events.

**Elements:**
- **Filter bar:**
  - Action type dropdown: All, Leave Submitted, Ticket Created, Password Reset, Intent Created, Intent Updated, Template Edited, etc.
  - Date range picker (from / to)
  - Actor filter (search by name)
- **Results table:**
  - Timestamp
  - Actor (name)
  - Action (human-readable: "Submitted leave request")
  - Reference ID (LEAVE-2045, TKT-4021, etc.)
  - Details (expandable — shows JSONB details like leave type, dates, etc.)
- **Pagination:** Previous / Next, showing "1–50 of 142"

---

### 10. Admin — Conversation Logs

View recent conversations handled by this role pack's bot.

**Elements:**
- **Conversation list:**
  - User name / email
  - Started at (timestamp)
  - Message count
  - Last intent detected
  - Click to expand → full message transcript (read-only)
- **Expanded view:**
  - Full message thread (same styling as chat view, but read-only)
  - Each bot message shows: detected intent + confidence score
- **Pagination**

---

## Design Constraints

| Constraint | Requirement |
|------------|-------------|
| **Responsive** | Must work at desktop (1280px+) and mobile (375px+) widths. Sidebar collapses to hamburger on mobile |
| **Role scoping** | Admin console shows ONLY the logged-in admin's role pack data. The nav and page headers reflect their role (HR / IT / Admissions) |
| **Component reuse** | Chat message types (data card, slot prompt, confirmation, result, list) should be a shared component library — same components render across HR, IT, and Admissions |
| **States** | Every page needs designs for: loaded, loading, empty, and error states |
| **Accessibility** | Color alone should not convey meaning (use icons + labels for badges/statuses) |

---

## Page-to-Feature Map

This shows which team member builds which pages:

| Page | Built by |
|------|----------|
| Login | Platform |
| Home / Conversation List | Platform |
| New Conversation | Platform |
| Chat View (shell + message components) | Platform builds the framework; HR/IT/Admissions build their role-specific cards |
| Talk Mode | Platform |
| Admin — Intent List | Platform builds framework; HR/IT/Admissions populate for their role |
| Admin — Create/Edit Intent | Platform builds framework + "Generate Similar"; HR/IT/Admissions use it |
| Admin — Retraining | Platform |
| Admin — Audit Log | Platform |
| Admin — Conversation Logs | Platform |
