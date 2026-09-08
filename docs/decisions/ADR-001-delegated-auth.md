# ADR 001: Delegated Authentication

**Date:** 2026-09-08  
**Status:** Accepted  

## Context
VARIO is designed as an integratable framework for organizations to orchestrate departmental workflows (HR, IT, Admissions) via voice and text. Early specifications (PRD/SRS) included a full native authentication system within VARIO, complete with self-registration, email verification, password reset, and account lockouts.

However, as an enterprise tool, requiring users to create and manage a separate set of credentials specifically for VARIO creates friction and security fragmentation. Real-world organizations rely on central identity providers (Active Directory, Okta, etc.) for employee and student access.

## Decision
We will strip native user management out of VARIO and use a **Delegated Authentication model**. 

- VARIO will provide a login interface that collects credentials.
- These credentials will be passed to an **Auth Adapter**, which verifies identity against the organization's existing identity provider.
- For development and demo purposes, we will build a **Mock Auth Service** (pre-seeded with test users) to simulate the organization's identity provider, following the exact same pattern used for Mock HRMS and Mock ITSM.
- Upon successful validation by the Auth Adapter, VARIO will issue its own JWT containing the user's ID, email, and role claim. This JWT will be used for all subsequent authorization within VARIO.
- The `users` database table will transition from a master record (storing password hashes and verification states) to a lightweight cache that is upserted upon login based on data returned by the Auth Adapter.

## Consequences
- **Positive:** VARIO aligns perfectly with enterprise integration patterns. The system is leaner, reducing the data model from 10 tables to 9 (removing `auth_tokens`), and completely removing the need for VARIO to send emails (Gmail SMTP dependency removed).
- **Positive:** Development effort for Member B is significantly reduced in Sprint 1, allowing them to focus on core platform capabilities earlier.
- **Negative:** Deviates from the original PRD/SRS. Instructors/evaluators must be made aware of this architectural pivot via this ADR.
