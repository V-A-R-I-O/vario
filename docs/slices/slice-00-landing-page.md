
# Slice 00 — VARIO Landing Page

**Sprint:** 1  
**Owner:** A (Pavan Kishor)  
**Module:** Frontend / Public Project Entry  
**Status:** Completed

## Goal

Build the public-facing VARIO landing page as the entry point to the project. The page should explain what VARIO is, communicate its role-adaptive voice-assistant architecture, present the primary enterprise use cases, and provide clear paths to the application, repository, and documentation.

Slice 00 is a small frontend foundation slice. It does not replace or renumber any existing slice.

## What to Build

### Hero

- VARIO branding
- Full project name: Voice Adaptive Role & Intent Orchestrator
- Concise value proposition
- Primary CTA to enter the application
- Secondary CTA to the GitHub repository and/or documentation

### Project Overview

Explain:

- What VARIO is
- The role of voice/text interaction in the system
- Why role-aware orchestration is useful for enterprise workflows
- That the platform is modular and extensible

### How VARIO Works

Present the core flow clearly:

```
User
  ↓
Voice / Text
  ↓
Intent + Context
  ↓
Role-aware Orchestration
  ↓
Role Pack
  ↓
Enterprise Service
  ↓
Response
```

### Key Capabilities

Highlight the capabilities already established by the project architecture:

- Role-aware interaction
- Voice and text interaction
- Multi-turn conversational workflows
- HR, IT Support, and Admissions role packs
- Enterprise service integration through adapters
- Extensible architecture
- Open-source development

### Architecture Overview

Provide a concise, user-readable architecture overview covering the existing major layers:

- Frontend
- Gateway
- Core orchestration
- Role packs
- Integration adapters
- Mock enterprise services
- Database

The landing page should explain the architecture without exposing implementation secrets or deployment credentials.

### Enterprise Use Cases

Include the current role domains:

- HR self-service
- IT support
- Admissions

### Open-source / Project Section

Include:

- GitHub repository link
- Documentation link when available
- Apache License 2.0 information

### Footer

Include the project name and relevant repository, documentation, and license links.

## Acceptance Criteria

- [x] Landing page is reachable from the frontend public entry route.
- [x] VARIO name and project purpose are immediately understandable.
- [x] Hero contains primary and secondary calls to action.
- [x] Page explains the voice/text → intent → role → service flow.
- [x] HR, IT Support, and Admissions use cases are represented.
- [x] Architecture is explained at a high level.
- [x] GitHub and documentation links are functional.
- [x] Apache License 2.0 information is represented.
- [x] Page is responsive on desktop and mobile widths.
- [x] Existing frontend lint/test/build checks pass.
- [x] Landing page can be viewed without authentication.
- [x] Existing authentication and application flow remain functional.

## Out of Scope

- Voice-processing implementation
- Authentication implementation
- Backend/API changes
- Rasa implementation
- Role-pack functionality
- Production deployment configuration
- New frontend framework
- New UI library unless already used by the existing frontend
- Redesign of the authenticated application
- Analytics implementation
- Secrets, credentials, or environment values in client-visible content

## Dependencies

- Use the existing `frontend/` application and its established Next.js conventions.
- Reuse existing project branding/components where appropriate.
- Do not create a separate landing-page application.
- Do not renumber or modify the scope of existing slices 01–31.

## Review

This is a normal frontend slice. Additional security review is only required if implementation touches authentication, deployment configuration, environment variables, or secrets.

## Commit / PR Convention

Use the slice identifier in commits and PRs, for example:

```
slice-00-landing-page: add VARIO public landing page
```
