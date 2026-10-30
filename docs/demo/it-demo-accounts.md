# VARIO demo account reference — ITSM fixtures

These accounts are deterministic **local/demo-only** fixtures. They are not production identities. The mock authentication service uses the demo password `password123` for seeded users.

| Login | External ID | Role | Mock ITSM security question | Demo answer |
|---|---|---|---|---|
| emp1@org.example.com | EMP-1001 | end_user | What was the name of your first school? | sunrise |
| hr@org.example.com | EMP-2001 | hr_admin | What is your favorite book? | the hobbit |
| it@org.example.com | EMP-3001 | it_admin | What was your first work location? | north campus |
| admissions@org.example.com | EMP-4001 | admissions_admin | What was your first work location? | south campus |
| pavan@org.example.com | EMP-1010 | end_user | What was your first work location? | north campus |
| tahir@org.example.com | EMP-1011 | end_user | What was your first work location? | north campus |
| rohith@org.example.com | EMP-1012 | end_user | What was your first work location? | north campus |
| mitesh@org.example.com | EMP-1013 | end_user | What was your first work location? | north campus |
| applicant@org.example.com | APP-2026-001 | end_user / applicant | What is your application reference? | applicant one |

## Ticket identity rules

- ITSM ticket IDs use the canonical `IT-####` format (for example, `IT-1001`).
- Employee and admin identities can use the ITSM identity-verification flow.
- The applicant identity may create an IT support ticket as a reporter, but is deliberately not eligible for the employee password-reset flow.
- Ticket creation uses the authenticated `metadata.auth_context` identity; never trust an employee ID typed into the conversation as the reporter.

## Safety

Do not reuse these credentials or security answers outside the local mock environment. Never connect these fixtures to a production identity provider.
