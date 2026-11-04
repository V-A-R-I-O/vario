# Demo Test Scenarios

Step-by-step checks for the whole VARIO demo: login, the three role packs, voice, the admin console, security, and running it across several laptops. For each step you type a message, see what happens, and check it against the **Expect** column.

**Before you start**

- **Setup:** the stack runs on laptop C (see `docs/demo/local-demo.md`), and `docker compose ps` shows every service healthy. Open `http://<C's IP>:3000`, or `http://localhost:3000` on laptop C.
- **Password:** every account uses `password123`.
- **Wording varies.** Many replies come from templates with several variants, so the exact words can change between runs. Check the **facts**: numbers, IDs, statuses, which card appears and what it contains. Text in quotes is what the bot said in our own test run, so treat it as a sample.
- **Recording results:** note each scenario ID as Pass or Fail in the results sheet at the end. For a Fail, write down what you typed, what you saw, the account and the laptop.
- **Each scenario starts in a new conversation** (**New conversation**, then pick the pack) unless it says otherwise.

## Reference data

These come from the mock systems. Use them to check the bot's answers.

**Leave balances (mock-HRMS)**

| Account | Employee ID | Casual | Sick | Earned | Total | Past leave |
|---|---|---|---|---|---|---|
| `emp1@org.example.com` | EMP-1001 | 6 | 8 | 14 | 28 | LEAVE-2031, casual, 10–11 Sep 2026, approved |
| `pavan@org.example.com` | EMP-1010 | 6 | 8 | 14 | 28 | LEAVE-2025, casual, 10–11 Aug 2026, approved |
| `tahir@org.example.com` | EMP-1011 | 5 | 7 | 12 | 24 | none |
| `rohith@org.example.com` | EMP-1012 | 4 | 6 | 10 | 20 | none |
| `mitesh@org.example.com` | EMP-1013 | 5 | 8 | see `mock-hrms-service/app/seed_data.py` | — | none |

**IT tickets (mock-ITSM)**
- IT-1001: hardware, "Laptop battery drains quickly", **In Progress**
- IT-1002: access, "Cannot access the analytics portal", **Open**
- IT-1003: software, "VPN client installation request", **Resolved**
- New tickets get the next number (IT-1004, IT-1005, …).

**IT security answers**
- emp1: `sunrise` (question: "first school")
- pavan, tahir, rohith, mitesh and it@: `north campus` (question: "first work location")
- hr@: `the hobbit`
- admissions@: `south campus`

**Applications (mock-Admissions)**

| Application | Program | Status |
|---|---|---|
| APP-1001 | Computer Science (B.Tech) | Under Review |
| APP-1002 | Data Science (M.Tech) | Accepted (deposit due by 15 Nov 2026) |
| APP-1003 | Computer Science (B.Tech) | Documents Pending |
| APP-1004 | MBA | Rejected |

**Program names the bot understands**
- B.Tech: `btech`, `b.tech`, `computer science`, `cs`
- M.Tech: `mtech`, `m.tech`, `data science`, `ds`
- MBA: `mba`, `business administration`, `management`

---

## 1. Login and navigation

**L1: Successful login**
| Step | You do | What happens | Expect |
|---|---|---|---|
| 1 | Open the URL | Login page | Page loads with no errors |
| 2 | Log in as `rohith@org.example.com` / `password123` | You land on home | Home shows the HR, IT Support and Admissions packs |

**L2: Wrong password**
| 1 | Log in as `rohith@…` with password `wrong` | Login fails | "Invalid email or password". You stay on the login page. |

**L3: Unknown account**
| 1 | Log in as `nobody@org.example.com` / `password123` | Login fails | The same "Invalid email or password" message. It doesn't reveal whether the account exists. |

**L4: Empty fields**
| 1 | Click log in with an empty email or password | Login doesn't go through | A validation message, and no crash |

**L5: Login limit per account**
| 1 | Log in as `pavan@…` with a wrong password 11 times within a minute | The 11th attempt is refused | "Rate limit exceeded. Try again in N seconds." |
| 2 | Immediately log in as `tahir@…` with the right password (any laptop) | Login succeeds | One account's limit doesn't block another presenter |
| 3 | Wait one minute, then log in as `pavan@…` correctly | Login succeeds | The limit clears after a minute |

**L6: Log out**
| 1 | Click **Log out** | You return to login | Going back or opening `/home` asks you to log in again |

**L7: Admin accounts open the admin console**
| 1 | Log in as `hr@org.example.com` | The admin console opens, or a link to it is shown | The admin pages are scoped to HR |

**L8: An employee can't open admin pages**
| 1 | As `rohith@…`, open `http://<C-IP>:3000/admin` | Access is blocked | You're redirected or see an access error. No admin data is shown. |

---

## 2. Chat basics and UI

**U1: New conversation**
| 1 | Click **New conversation**, pick HR | An empty chat opens | The conversation appears in the list on the left |

**U2: Buttons send their value**
| 1 | HR: "apply for leave" | The bot asks for the leave type, with buttons (Casual / Sick / Earned) | A `slot_prompt` card with options |
| 2 | Click **Sick** | Your message shows as the button's value | The bot moves on to the start date |

**U3: Only the latest buttons are clickable**
| 1 | After U2, scroll up and click an older button | Nothing happens | Old buttons are disabled |
| 2 | Click a button while a reply is still loading | Nothing happens | Buttons are disabled while a message is in flight |

**U4: Confirmation buttons**
| 1 | Finish a leave request (H6) up to the confirmation card | The card shows the request's details as rows | It has **Confirm** and **Cancel** buttons |
| 2 | Click **Cancel** | The request is cancelled | A cancellation message appears and nothing is submitted |

**U5: History and cards survive a reload**
| 1 | After any conversation with cards (balance, ticket, checklist), press F5 | The page reloads | Every message **and every card** (rows, lists, reference IDs) is still there (M12) |

**U6: Conversation list**
| 1 | Have one HR, one IT and one Admissions conversation | The list shows all three | Each shows its pack and last activity. Clicking one opens it with its full history. |

**U7: Conversations are separate**
| 1 | In an HR conversation, start a leave request and stop at "start date" | — | — |
| 2 | Open a second HR conversation and type "what's my leave balance" | A balance card | The second conversation isn't stuck in the first one's form |
| 3 | Go back to the first conversation and type a date | The form continues there | Each conversation keeps its own state |

**U8: Long message**
| 1 | Type a 500-character paragraph | The bot replies normally | No crash, and the layout doesn't break |

**U9: Empty message**
| 1 | Try to send an empty message, or only spaces | Nothing is sent | Send is ignored or disabled |

**U10: Card gallery (optional)**
| 1 | Open `/home/chat/gallery` | A page showing every card type | All 9 types render: text, data card, prompt, confirmation, result, not found, FAQ, error, list |

---

## 3. HR pack

Log in as `rohith@org.example.com` unless a scenario says otherwise.

**H1: Leave balance**
| 1 | "what's my leave balance" | A balance card (title like "Rohith's leave balance") | Total 20: casual 4, sick 6, earned 10. Sample: "Your current leave balance is 20 days (4 casual, 6 sick, 10 earned)." |

**H2: Other balance phrasings**
| 1 | "how many leaves do I have left" | Balance card | Same numbers as H1 |
| 2 | "show my leave balance" | Balance card | Same numbers |

**H3: A typed employee ID is ignored** (B6/M2a)
| 1 | "what is the leave balance of EMP-1001" | Balance card | It shows **Rohith's own** balance (20), never EMP-1001's (28) |

**H4: Each presenter sees their own balance**
| 1 | Log in as `tahir@…` and ask "what's my leave balance" | Balance card | Total 24 (5 / 7 / 12) |
| 2 | Log in as `emp1@…` and ask the same | Balance card | Total 28 (6 / 8 / 14) |

**H5: Leave request with the type in the first message**
| 1 | "apply for casual leave" | "What is the start date for your leave (YYYY-MM-DD or e.g. 'tomorrow')?" | It doesn't ask for the type again |
| 2 | A date 10 days from today, e.g. `2026-11-14` | "What is the end date for your leave (YYYY-MM-DD)?" | — |
| 3 | The next day, e.g. `2026-11-15` | "Please provide a reason for your leave request." | — |
| 4 | "family function" | A confirmation card, "Confirm leave request" | Rows: Leave type casual, Start 2026-11-14, End 2026-11-15, Reason family function. **The start date must stay what you typed** (A2-06). |
| 5 | Click **Confirm** | A result card | "All set! Your leave request reference is LEAVE-20xx." The reference ID is shown on the card. |

**H6: Leave request without the type**
| 1 | "I want to apply for leave" | The type question, with Casual / Sick / Earned buttons | — |
| 2 | Click **Earned** | Start date question | — |
| 3–5 | Dates, reason, **Confirm** | As in H5 | The confirmation shows type earned |

**H7: Natural dates** (N5)
| 1 | "apply for sick leave" | Start date question | — |
| 2 | "tomorrow" | End date question | Accepted |
| 3 | Tomorrow's date as YYYY-MM-DD | Reason question | — |
| 4 | "fever" | Confirmation card | The start date is tomorrow's actual date. A free-text reason like "fever" is accepted, with no "please rephrase" prompt mid-form. |

**H8: Start date in the past**
| 1 | "apply for casual leave" | Start date question | — |
| 2 | `2026-01-01` | The bot refuses | It says the date can't be in the past and asks again, or shows an error. No request is created. |

**H9: End date before start date**
| 1 | "apply for casual leave", then start `2026-11-20` | End date question | — |
| 2 | `2026-11-18` | The bot refuses | It says the start date can't be after the end date and asks again, or shows an error. Nothing is submitted. |

**H10: Not enough balance**
| 1 | As `rohith@…` (casual 4): "apply for casual leave", start in 10 days, end 6 days later, reason "trip", **Confirm** | The submission is refused | It says the casual balance is insufficient (requested 7 days, only 4 available). No reference ID. |

**H11: Invalid date text**
| 1 | During a leave request, at the start date step: "banana" | The bot asks again | The question repeats, with no crash and no "please rephrase" |

**H12: Cancel at every step**
| 1 | Start a leave request, then type "cancel" at the **type** step | "Leave request cancelled. All details have been cleared." | The form ends |
| 2 | Repeat, cancelling at **start date**, **end date**, **reason**, and at the **confirmation** (Cancel button) | The same cancellation each time | It cancels from every step |

**H13: Goodbye mid-form**
| 1 | Start a leave request, then type "bye" at the reason step | A goodbye reply | The form ends |

**H14: A question mid-form, then back to the form** (M1a)
| 1 | "apply for casual leave" | Start date question | — |
| 2 | "what's my leave balance" | The balance card, then the start date question again | It answers, then **returns to the step it was on** |
| 3 | "what is the maternity leave policy" | The maternity answer, then the start date question again | Same |

**H15: Leave status** (N8)
| 1 | As `emp1@…`: "what is the status of my leave request" | Status of the latest request | LEAVE-2031, approved |
| 2 | As `rohith@…`, **after H5**: same question | Status of the new LEAVE-20xx | The request you just submitted |
| 3 | As `tahir@…` (no history): same question | — | It says there are no leave requests, with no error |

**H16: Policy topics** (each answer comes from its own policy)
| 1 | "what is the maternity leave policy" | FAQ card, "Maternity Leave Policy" | "26 weeks of paid maternity and adoption leave" |
| 2 | "what is the paternity leave policy" | FAQ card | The paternity policy, not the maternity one |
| 3 | "how many sick leaves can I take" or "sick leave policy" | FAQ card | The sick leave policy |
| 4 | "what is the bereavement leave policy" | FAQ card | The bereavement / compassionate leave policy |
| 5 | "can I carry forward my unused leave" | FAQ card | The carry-forward policy |
| 6 | "what is the work from home policy" | FAQ card | The WFH and hybrid policy |
| 7 | "tell me the leave policy" | FAQ card | The annual and statutory leave policy |

**H17: A policy that isn't covered**
| 1 | "what is the travel reimbursement policy" | The bot says it can't help with that topic | No made-up policy. It points to the topics it can answer. |

**H18: Greeting and goodbye**
| 1 | "hi" | A greeting | It mentions what HR can help with |
| 2 | "bye" | A goodbye | — |

**H19: Gibberish**
| 1 | "asdkjh qwe" | "I'm not sure I understood that. Could you rephrase it, or give me a little …" | The clarification prompt, with no crash |

**H20: Confirm and cancel by typing**
| 1 | At the confirmation step, type "confirm" | The same as clicking Confirm | Submitted |
| 2 | In another request, type "cancel" at the confirmation | The same as clicking Cancel | Cancelled |

---

## 4. IT support pack

Log in as `rohith@org.example.com` unless a scenario says otherwise.

**I1: Ticket status with an ID**
| 1 | "what is the status of ticket IT-1002" | A data card, "Ticket IT-1002" | Status **Open**. Sample: "Ticket IT-1002 is currently Open." |
| 2 | "status of IT-1001" | Data card | **In Progress** |
| 3 | "is IT-1003 resolved" | Data card | **Resolved** |

**I2: Ticket status without an ID**
| 1 | "check my ticket status" | "Please provide your ticket ID (for example, IT-1001) so I can check its status." | — |
| 2 | "IT-1003" | Data card | Resolved |

**I3: "Still open?" phrasing** (M4c)
| 1 | "is my ticket still open?" | Asks for the ticket ID | It's treated as a status question, not a new ticket |

**I4: Ticket that doesn't exist**
| 1 | "status of ticket IT-9999" | A "not found" card | It says the ticket wasn't found, with no crash |

**I5: Wrong ID format**
| 1 | "check my ticket status", then "INC-1001" | The bot asks again | Only the IT-#### format is accepted |
| 2 | "IT-12" | Asks again | — |
| 3 | "cancel" | "Okay, I've cancelled that request." | The form ends (M3b) |

**I6: Raise a ticket, the full flow**
| 1 | "my laptop screen is broken" | "What category best describes the issue?" with buttons: Hardware, Software, Network, Access, Email, Other | — |
| 2 | Click **Hardware** | "Please describe the issue. Include what happened and any useful error message, but do not include passwords or other secrets." | — |
| 3 | "the screen flickers and goes black" | A confirmation card, "Confirm IT support ticket" | Rows: Category hardware, Description (your text), Reporter **your own employee ID** (EMP-1012) |
| 4 | Click **Confirm** | A result card | "Your support ticket IT-10xx has been created." The ID is on the card. |
| 5 | "status of IT-10xx" (the new ID) | Data card | Open |

**I7: Each category**
| 1 | Repeat I6 with Software, Network, Access, Email and Other | A ticket each time | The confirmation shows the category you chose |

**I8: Typing the category**
| 1 | "I need help with my email", then type "network" | It goes to the description step | Typed categories work like the buttons |

**I9: Invalid category**
| 1 | "raise a ticket", then "banana" | "Choose hardware, software, network, access, email, or other." and it asks again | No ticket created |

**I10: Cancel at every step** (A2-21)
| 1 | "my mouse is broken", then "cancel" at the **category** step | "Okay, I've cancelled that request." | The form ends. It must **not** re-ask the category. |
| 2 | Repeat, cancelling at the **description** step | Cancelled | — |
| 3 | Repeat, clicking **Cancel** at the **confirmation** | Cancelled | No ticket created |

**I11: "no" at the confirmation**
| 1 | Get to the confirmation, then type "no" | Not submitted | The request stops, and no ticket ID appears |

**I12: Duplicate ticket** (FR-13)
| 1 | Raise a ticket: Hardware, "keyboard keys are stuck", Confirm | IT-10xx | — |
| 2 | In the same conversation, raise the identical ticket again | — | It returns the **same ticket ID** instead of creating a second one |

**I13: Greeting or goodbye mid-form**
| 1 | "raise a ticket", then "hi" at the category step | A greeting | The form ends |
| 2 | "raise a ticket", then "bye" | A goodbye | The form ends |

**I14: Password reset, your own account**
| 1 | "I forgot my password" | "Please confirm your employee ID (for example, EMP-1001). I can only reset the password for your signed-in account." | — |
| 2 | "EMP-1012" (your own) | "To verify your identity, please answer: What was your first work location?" | The question is for your own account |
| 3 | "north campus" | A result card | "Password reset has been initiated for EMP-1012." |

**I15: Password reset with someone else's ID** (A2-13)
| 1 | "I forgot my password" | Asks for the employee ID | — |
| 2 | "EMP-1001" | It explains it can only reset **your** account (EMP-1012), then asks your security question | It doesn't loop, and it never asks EMP-1001's question |
| 3 | "north campus" | Reset initiated for **EMP-1012** | — |

**I16: Wrong security answer**
| 1 | Start a reset with your own ID, then answer "wrong place" | It says the answer is wrong and how many attempts are left | Not reset |
| 2 | Answer correctly | Reset initiated | — |

**I17: Lockout after 3 wrong answers** (use a spare account, e.g. `mitesh@…`)
| 1 | Answer wrongly 3 times, across one or more resets | — | "Too many failed verification attempts. Contact IT Support." |
| 2 | Try a new reset | Still locked | The lock persists, even after restarts |

To unlock for the next rehearsal, run on laptop C: `docker compose exec mock-itsm rm -f /data/identity-attempts.json`, or reset everything with `docker compose down -v`.

**I18: The security answer is never shown or stored**
| 1 | After I14, reload the page | — | Your answer message shows as **"[security answer redacted]"**, not "north campus" |
| 2 | As `it@…`, open Conversation logs and find this chat | — | The transcript also shows "[security answer redacted]" |

**I19: An applicant can't reset an employee password**
| 1 | As `applicant@…`: "I forgot my password" | It refuses | It says applicants aren't eligible for the employee reset flow |

**I20: An applicant can raise a ticket**
| 1 | As `applicant@…`: "my laptop screen is broken", then Hardware, a description, Confirm | Ticket created | Reporter APP-2026-001 |

**I21: Ticket created by an admin account** (M7c)
| 1 | As `it@…`, raise a ticket in an IT conversation | Ticket created | It works like any other user, with reporter EMP-3001 |

---

## 5. Admissions pack

Log in as `applicant@org.example.com` unless a scenario says otherwise.

**A1: Status with an ID**
| 1 | "what is the status of application APP-1001" | A data card, "Application APP-1001 Status" | **Under Review**, plus the next step |
| 2 | "status of APP-1002" | Data card | **Accepted**: pay the ₹50,000 deposit by 15 Nov 2026 |
| 3 | "check APP-1003" | Data card | **Documents Pending**: upload the Class 12 and Migration certificates |
| 4 | "what happened to APP-1004" | Data card | **Rejected**: reapply in spring or contact counselling |

**A2: Status without an ID**
| 1 | "what is my application status" | It asks for the application ID | — |
| 2 | "APP-1002" | Data card | Accepted |

**A3: Application that doesn't exist**
| 1 | "status of APP-9999" | A "not found" card | It says the application wasn't found |

**A4: Wrong ID format**
| 1 | "what is my application status", then "12345" | It asks again | Only the APP-#### format is accepted |

**A5: Document checklist for each program**
| 1 | "what documents do I need for btech" | A list card, "Required Documents — Computer Science (B.Tech)" | Class 10 and Class 12 certificates, and so on |
| 2 | "documents for mtech" | List card | Data Science (M.Tech) |
| 3 | "checklist for mba" | List card | MBA |
| 4 | "what do I need for computer science" or "cs" | List card | B.Tech (the alias works) |

**A6: Checklist without a program**
| 1 | "what documents are required" | It asks which program, with buttons | — |
| 2 | Click a program | List card | That program's documents |

**A7: Unknown program**
| 1 | "documents for medicine" | Not found, or it asks again | No made-up checklist |

**A8: Fees and deadlines**
| 1 | "when is the last date to pay fees" | A data card, "Admissions Calendar (2026-2027)" | Deadlines, including "Regular Application Submission Deadline: November 30, 2026" |
| 2 | "how much is the tuition fee for B.Tech" | Data card | The fee details |
| 3 | "what are the admission deadlines" | Data card | The deadlines |

**A9: Switching topics** (M3c)
| 1 | "what is my application status" (it asks for the ID) | — | — |
| 2 | Instead: "when is the last date to pay fees" | The fee answer | It switches topic and doesn't stay stuck asking for the ID |
| 3 | "what documents do I need for mba" | List card | — |

**A10: Follow-ups** (N13)
| 1 | "status of APP-1001" | Data card | — |
| 2 | "and APP-1002?" | Data card for APP-1002 | The follow-up works, and it doesn't reuse APP-1001 |

**A11: Greeting, goodbye and gibberish**
| 1 | "hello" | A greeting | — |
| 2 | "zzqq" | The clarification prompt | — |
| 3 | "bye" | A goodbye | — |

**A12: An employee using Admissions**
| 1 | As `rohith@…`, open Admissions: "status of APP-1001" | Data card | It works. Any signed-in user can look up any application ID; for the mock this is by design (FR-14). |

---

## 6. Robustness and failures

**X1: Low confidence outside a form** (FR-2)
| 1 | In any pack: "purple elephants dancing" | "I'm not sure I understood that. Could you rephrase it…" | No workflow starts |

**X2: Low confidence inside a form**
| 1 | HR leave request, at the reason step: "uhh not sure, family stuff" | It's accepted as the reason | No "please rephrase" mid-form |

**X3: A pack is down** (M6)
| 1 | On laptop C: `docker compose stop rasa-hr` | — | — |
| 2 | In HR, type anything | An error card: "The HR assistant is unavailable right now. Please try again in a moment." | No crash or blank page. Your message is still in the history. |
| 3 | In IT or Admissions, type anything | Normal replies | The other packs are unaffected |
| 4 | `docker compose start rasa-hr`, wait 1–2 minutes until `docker compose ps` shows it healthy | — | — |
| 5 | In HR: "what's my leave balance" | Balance card | It's back |

**X4: A backend system is down**
| 1 | `docker compose stop mock-itsm` | — | — |
| 2 | IT: "status of IT-1002" | An error card | It says the ticket system is unavailable. No made-up status. |
| 3 | `docker compose start mock-itsm` and ask again | Data card | Recovered |

Repeat with `mock-hrms` (HR balance) and `mock-admissions` (application status).

**X5: The gateway restarts mid-demo**
| 1 | `docker compose restart gateway` while logged in | — | — |
| 2 | After about 20 seconds, send a message | A normal reply | You stay logged in (tokens survive), and the history is intact |

**X6: A form survives a Rasa restart**
| 1 | HR: "apply for casual leave", then enter the start date | End date question | — |
| 2 | `docker compose restart rasa-hr`, wait until healthy | — | — |
| 3 | Type the end date | The reason question | The form continues where it was (trackers live in Postgres) |

**X7: Rapid messages**
| 1 | Send 5 messages quickly, one after another | — | Each gets one reply, in order, with no duplicates or crash |

**X8: Chat rate limit (optional)**
| 1 | Send more than 30 messages in one minute as one user | — | After 30: "Rate limit exceeded…", and it recovers after a minute |

---

## 7. Talk mode (voice)

Talk mode uses Chrome's speech recognition, so the client laptop needs internet. On `http://<C-IP>:3000` the microphone only works after the Chrome flag described in the runbook (§3.5), or through the tunnel. On laptop C, `http://localhost:3000` works directly.

**V1: Speak a question**
| 1 | In HR, click the **Talk mode** mic button and allow the microphone | It starts listening | — |
| 2 | Say "what is my leave balance" | Your words appear as your message | The balance card, the same as typing |

**V2: Spoken replies (TTS key configured)**
| 1 | After V1 | The reply plays aloud | You hear the reply text. **Replay audio** plays it again. |

**V3: No TTS key**
| 1 | If `secrets/gcp-tts-sa.json` is missing | The reply arrives as text | No error. Talk mode falls back to text only. |

**V4: Nothing said**
| 1 | Click the mic and stay silent | It stops listening | A hint to try again, and nothing is sent |

**V5: A multi-step form by voice**
| 1 | Say "apply for sick leave", then "tomorrow", and so on | The form progresses | Each spoken answer fills the next step |

**V6: Microphone blocked**
| 1 | On a client without the flag, at `http://<C-IP>:3000`, click the mic | — | A clear message that the mic isn't available. Text chat still works. |

**V7: Browser without speech recognition**
| 1 | Open in Firefox | — | The mic button is hidden or explains it's unsupported. Text works. |

---

## 8. Admin console

Log in as `hr@org.example.com`. Then repeat the main flows (AD1, AD3, AD9, AD10) as `it@…` and `admissions@…`.

**AD1: Intents list**
| 1 | Open **Intents** | A list of HR intents | Each is marked **Dynamic workflow** (read-only, e.g. check_leave_balance) or **Static FAQ** (editable), plus **Needs retrain** or **Up to date** |
| 2 | Look for IT or Admissions intents | None | Only the HR pack is shown |

**AD2: Open a dynamic workflow**
| 1 | Click `check_leave_balance` | The intent page opens | Read-only: you can't rename or delete it |

**AD3: Create a static FAQ**
| 1 | **New intent**. Name `ask_parking_policy`, add 5+ training phrases ("where can I park", "parking rules", "is there employee parking", "car parking at office", "where do I leave my car"), response template "Employee parking is in basement B2. Show your ID at the gate." | The FAQ is saved | It appears in the list as Static FAQ, **Needs retrain** |
| 2 | As `rohith@…`, ask HR "where can I park" | — | **Not answered yet**, since it isn't trained. You get something else or the clarification prompt. |

**AD4: Duplicate name**
| 1 | Create another intent named `ask_parking_policy` | It's refused | "Intent name already exists…" |

**AD5: No training phrases**
| 1 | Create an intent with a name and template but no phrases | It's refused | "At least one training phrase is required" |

**AD6: Generate similar phrases (needs `GEMINI_API_KEY`)**
| 1 | On the FAQ, click generate | Suggested phrases appear | **Accept**, **Reject** and **Accept edited** each work |
| 2 | Without a Gemini key | — | No suggestions, with no crash; type the phrases yourself |

**AD7: Response variants**
| 1 | With **Allow rephrasing** on and a Gemini key, save the template | Variants are generated | Several wordings appear under the template |
| 2 | Delete one variant | It's removed | — |
| 3 | Edit only the training phrases and save | — | The **existing variants stay** (M9a) |
| 4 | Change the template's base text | — | The variants are regenerated |

**AD8: Edit an FAQ**
| 1 | Add a phrase "parking slot for employees" and save | Saved | Status **Needs retrain** |
| 2 | Remove a phrase and save | Saved | Needs retrain |

**AD9: Retrain**
| 1 | Open **Retraining** | The page shows modified intents (e.g. ask_parking_policy) | — |
| 2 | Click **Retrain** | The job starts: pending, then training | Use **Refresh status** to update it |
| 3 | Wait 1–3 minutes | The job shows **complete** | The intents now show **Up to date**, and **Last completed job** has the time |
| 4 | As `rohith@…`, ask HR "where can I park" | The FAQ answer | "Employee parking is in basement B2…" |
| 5 | Ask HR "what's my leave balance" | Balance card | Existing flows still work after retraining |

**AD10: Retraining a pack doesn't affect the others**
| 1 | After AD9, ask IT "where can I park" | — | IT doesn't know the HR FAQ (the clarification prompt, or something else) |

**AD11: Retrain limit**
| 1 | Click Retrain 4 times within an hour as the same admin | The 4th is refused | "Rate limit exceeded…" (3 per hour) |
| 2 | Click Retrain while a job is running | It's refused | "A retraining job is already running for this role pack." |

**AD12: A retrain survives a restart**
| 1 | After AD9: `docker compose up -d --force-recreate rasa-hr`, wait until healthy | — | — |
| 2 | Ask HR "where can I park" | The FAQ answer | The retrained model came back from its volume |

**AD13: Delete an FAQ**
| 1 | Delete `ask_parking_policy` | Removed | It disappears from the list |
| 2 | Retrain, then ask "where can I park" | — | No longer answered with that FAQ |
| 3 | Try to delete a dynamic workflow | It's refused | "Dynamic workflows cannot be deleted" |

**AD14: Edit an FAQ's answer**
| 1 | On an existing FAQ (e.g. ask_wfh_policy, if it's a Static FAQ), change the template text and save | Saved | — |
| 2 | Ask the question as an employee (no retrain needed for answer text) | The new text, or one of its variants | Template changes apply straight away |

**AD15: Conversation logs**
| 1 | Open **Conversation logs** | A list of HR conversations | Each shows the user, last intent, message count and last updated |
| 2 | Search for a user, e.g. "Rohith" | The list is filtered | — |
| 3 | Open one | The full transcript | Cards and intents are shown, and security answers appear as "[security answer redacted]" |
| 4 | Look for IT conversations | None | Only HR conversations are shown |

**AD16: Audit log**
| 1 | Open **Audit log** | A list of entries | intent created / updated / deleted entries from AD3–AD13, with actor and time |
| 2 | Filter by action, actor and date range | The list is filtered | "No audit entries" when nothing matches |
| 3 | As `it@…`, after I6 and I14 | Entries for those | **ticket_created** with the ticket ID, and **password_reset_initiated** with the employee ID (A2-10). No "unknown" entries. |

**AD17: Admin scope by URL**
| 1 | As `hr@…`, open an IT intent's URL (copy one from the `it@…` session) | It's refused | "Intent belongs to another role pack" or an access error |

**AD18: Each admin sees only their own pack**
| 1 | Repeat AD1 and AD15 as `it@…` and `admissions@…` | — | Each sees only their own pack's intents, conversations and audit entries |

---

## 9. Security and privacy

**S1: Identity comes from the login, not from what you type**
| 1 | Run H3 and I15 | — | Your own employee ID is used every time |

**S2: Security answers are redacted everywhere**
| 1 | Run I18 | — | The chat history and admin logs show "[security answer redacted]" |

**S3: The API is unreachable without a login**
| 1 | In a new private window, open `http://<C-IP>:3000/api/conversations` | It's refused | 401 "Missing or invalid token" |

**S4: Only port 3000 is reachable from other laptops**
| 1 | From a client, open `http://<C-IP>:8000/docs` and `http://<C-IP>:5005` | They don't connect | Only port 3000 answers |

**S5: The session expires (optional)**
| 1 | Set `JWT_EXPIRY_MINUTES=2` in `.env`, run `docker compose up -d`, log in and wait 3 minutes | The next action asks you to log in | The expired token is rejected cleanly |

Afterwards, set it back to `JWT_EXPIRY_MINUTES=60` and run `docker compose up -d`.

**S6: An employee can't call the admin API**
| 1 | As `rohith@…`, open `/admin/intents` | It's refused | 403, or redirected away |

---

## 10. Multiple laptops and network

**N1: Four laptops at once**
| 1 | Each presenter logs in from their own laptop with their own account | — | All succeed |
| 2 | Everyone runs H1 at the same time | — | Each sees their own balance |

**N2: The same account on two laptops**
| 1 | Log in as `tahir@…` on two laptops | — | Both work. Conversations from one appear on the other after a refresh. |

**N3: A client changes network**
| 1 | A client moves from the hotspot to another network | It can't connect | Expected. Rejoin the hotspot and reload. |

**N4: Laptop C's IP changes**
| 1 | Laptop C reconnects to the hotspot | It may get a new IP | Run `ipconfig` again and share the new URL |

**N5: Tunnel (optional)**
| 1 | On C: `cloudflared tunnel --url http://localhost:3000` | It prints an `https://…trycloudflare.com` URL | — |
| 2 | Open it on a phone, log in, and chat in each pack | — | Login, chat and the mic all work over HTTPS |

---

## 11. Persistence and resets

**P1: Data survives a full restart**
| 1 | `docker compose stop`, then `docker compose start`, wait until everything is healthy | — | — |
| 2 | Log in again | — | Conversations, cards, FAQs and audit entries are all still there |

**P2: Seeding is safe to repeat** (B3)
| 1 | `docker compose restart gateway` twice | — | No duplicated intents or templates in the admin console |

**P3: Full reset**
| 1 | `docker compose down -v`, then `docker compose up -d` | Fresh data | Old conversations are gone. Logins still work, and seeded intents are back. |

**P4: Mock data resets**
| 1 | `docker compose restart mock-hrms` | — | Balances return to the values in the reference table, and new leave requests are gone |
| 2 | `docker compose restart mock-itsm` | — | Tickets return to IT-1001…1003. Identity lockouts remain (see I17). |

---

## Results sheet

Copy this table and fill it in for each rehearsal.

| ID | Pass / Fail | Tester | Laptop | Notes (what you typed and saw, if it failed) |
|---|---|---|---|---|
| L1 | | | | |
| L2 | | | | |
| … | | | | |
| P4 | | | | |

**Checklist for the evaluation demo.** These are the headline scenarios to run on the day:
- L1, L5
- H1, H5, H14, H16
- I6, I10, I14, I18
- A1, A5, A8, A9
- X3
- V1, V2
- AD3, AD9, AD15, AD16
- N1
