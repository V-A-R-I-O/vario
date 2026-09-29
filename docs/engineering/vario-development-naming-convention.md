# VARIO GitHub ↔ Jira Development & Naming Convention

**Purpose:**  
Define a single naming and workflow standard for VARIO so that Jira issues, GitHub branches, commits, pull requests, reviews, CI results, and merges remain consistently traceable.

**Applies to:**  
All VARIO contributors, all slices, all GitHub branches, commits, pull requests, and Jira development work.

---

# 1. Source of Truth

VARIO uses the following responsibility model:

| System | Responsibility |
|---|---|
| Jira | Work item, ownership, status, sprint, planning |
| GitHub | Code, branches, commits, pull requests, reviews, CI/CD, merge |
| GitHub Reviewer | Authoritative source for the actual code reviewer |
| Jira Reviewer | Mirror of the actual GitHub reviewer, when configured |

Jira must never be used as a substitute for GitHub code-review state.

---

# 2. Primary Traceability Identifier

Every development task must have:

```text
Jira Issue Key + VARIO Slice ID
```

Example:

```text
Jira:  SCRUM-12
Slice: Slice 28 — CI/CD
```

The Jira issue key is the **authoritative integration identifier**.

The slice ID is the **VARIO architectural/workstream identifier**.

Therefore:

```text
SCRUM-12
slice-28-cicd
```

must refer to the same piece of work.

---

# 3. Branch Naming Standard

Use:

```text
feature/<jira-key>-<slice-id>-<short-name>
```

for feature work.

For VARIO slice work, the preferred format is:

```text
feature/scrum-12-slice-28-cicd
```

Examples:

```text
feature/scrum-12-slice-28-cicd
feature/scrum-13-slice-29-oci-cloudflare
feature/scrum-14-slice-30-vercel-neon
```

For bug fixes:

```text
fix/<jira-key>-<slice-id>-<short-name>
```

Example:

```text
fix/scrum-12-slice-28-cicd-test-command
```

For documentation:

```text
docs/<jira-key>-<slice-id>-<short-name>
```

Example:

```text
docs/scrum-12-slice-28-cicd-workflow
```

### Branch rules

1. Create the branch from the current `main`.
2. One Jira issue should normally have **one primary development branch**.
3. Additional branches are allowed only when technically necessary and must retain the same Jira key.
4. One primary branch must normally correspond to one slice.
5. Do not combine unrelated slices in the same branch or PR.
6. Do not create branches such as:

```text
test
new-feature
final
final2
rohit-work
changes
temp
fix
```

7. Never put secrets or credentials in branch names.
8. Keep branch names lowercase and predictable.
9. Jira keys in branch names use lowercase for consistency.

---

# 4. Commit Naming Standard

Every contributor-authored implementation commit must contain:

```text
<Jira-Key> <slice-id>: <imperative description>
```

Example:

```text
SCRUM-12 slice-28-cicd: add pull request CI workflow
```

Additional examples:

```text
SCRUM-12 slice-28-cicd: add backend test job
SCRUM-12 slice-28-cicd: add frontend test job
SCRUM-12 slice-28-cicd: fix pytest discovery
SCRUM-13 slice-29-oci-cloudflare: configure OCI deployment
```

### Commit rules

- Use the Jira key in its **canonical uppercase form**.
- Use the official slice ID.
- Use an imperative description.
- Keep the description concise.
- One logical change per commit where practical.
- Do not use vague messages such as:

```text
changes
update
fix
done
final
testing
stuff
```

### Automated commits

Automatically generated commits, such as GitHub-generated or dependency-management commits, are exempt from the contributor-authored commit naming requirement.

Where the automation supports Jira association, the corresponding Jira key should still be retained.

### Why both identifiers?

The Jira key provides direct Jira integration.

The slice ID provides VARIO-specific traceability.

---

# 5. Pull Request Naming Standard

Every PR title must contain both identifiers:

```text
[<Jira-Key>] <slice-id>: <short description>
```

Example:

```text
[SCRUM-12] slice-28-cicd: add pull request CI workflow
```

Other examples:

```text
[SCRUM-13] slice-29-oci-cloudflare: configure OCI deployment
[SCRUM-14] slice-30-vercel-neon: configure frontend deployment
```

The Jira key in the PR title is the **primary integration mechanism**.

The slice ID ensures the PR remains identifiable from VARIO project documentation.

---

# 6. Pull Request Body Standard

Every PR must contain:

```markdown
## Jira
SCRUM-12

## Slice
Slice 28 — CI/CD

## Branch
feature/scrum-12-slice-28-cicd

## What Changed
- Added pull request CI workflow
- Added backend test execution
- Added frontend test execution

## Acceptance Criteria
- [ ] PR CI executes automatically
- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Required checks are enforced

## Testing
- pytest
- Jest / React Testing Library

## Dependencies
- None

## Environment / Secrets
- No secret values committed
- Required environment variables documented in `.env.example`

## Review
- [ ] Code reviewed
- [ ] CI passing
- [ ] Acceptance criteria verified
```

The PR body must never contain actual secret values.

---

# 7. Jira ↔ GitHub Traceability Chain

Every development item should produce this chain:

```text
Jira Issue
   ↓
SCRUM-12
   ↓
Slice
   ↓
slice-28-cicd
   ↓
Branch
   ↓
feature/scrum-12-slice-28-cicd
   ↓
Commit(s)
   ↓
SCRUM-12 slice-28-cicd: ...
   ↓
Pull Request
   ↓
[SCRUM-12] slice-28-cicd: ...
   ↓
CI
   ↓
Review
   ↓
Approval / Changes Requested
   ↓
Merge
   ↓
Jira Done
```

This is the standard VARIO traceability path.

---

# 8. Jira Status Synchronization

GitHub events should drive development-state synchronization where integration/automation is configured.

| GitHub event | Jira result |
|---|---|
| Branch created | Development link, if the Jira/GitHub integration detects and associates it |
| PR opened | In Review |
| PR reopened | In Review |
| Changes requested | In Progress |
| New commit after changes requested | In Review |
| PR approved | In Review / Ready for Merge |
| PR merged | Done, if acceptance criteria are satisfied |
| PR closed without merge | Return to appropriate Jira state |

A branch existing in GitHub does **not by itself guarantee** that Jira will create a Development link. The result depends on the configured Jira/GitHub integration.

### Important

**Approval does not mean Done.**

The Jira issue becomes Done only after the corresponding PR is merged and the acceptance criteria are satisfied.

---

# 9. Reviewer Synchronization

GitHub is authoritative for reviewers.

Example:

```text
GitHub PR
Reviewer: Team Member A
        ↓
Jira Reviewer
Team Member A
```

Jira must not independently assign a different reviewer merely because a Jira field exists.

If a Jira `Reviewer` User Picker field is configured, it should mirror the actual GitHub reviewer after a PR exists.

Before a PR is opened, the Jira Reviewer field should not be treated as proof that the person is reviewing code.

---

# 10. Pull Request Review Lifecycle

The expected lifecycle is:

```text
PR Opened
    ↓
In Review
    ↓
Reviewer Assigned
    ↓
Review
    ├── Changes Requested
    │       ↓
    │   In Progress
    │       ↓
    │   New Commit
    │       ↓
    │   In Review
    │
    └── Approved
            ↓
      Ready to Merge
            ↓
         Merged
            ↓
           Done
```

This lifecycle must be implemented through the Jira/GitHub integration or automation.

Naming conventions make the events traceable; they do not replace the integration.

---

# 11. Jira Key Must Be Present in GitHub Work

For reliable synchronization:

### Branch

```text
feature/scrum-12-slice-28-cicd
```

### Commit

```text
SCRUM-12 slice-28-cicd: add CI workflow
```

### PR title

```text
[SCRUM-12] slice-28-cicd: add CI workflow
```

### PR body

```text
Jira: SCRUM-12
Slice: Slice 28 — CI/CD
```

This creates multiple independent traceability points.

If one mechanism fails to recognize the branch, the PR title/body and commit history still identify the Jira issue.

---

# 12. Slice ID Rules

Use the official slice identifier from:

```text
docs/slices/
```

The format is:

```text
slice-<two-digit-number>-<short-name>
```

Examples:

```text
slice-28-cicd
slice-29-oci-cloudflare
slice-30-vercel-neon
```

Do not invent alternate names for an existing slice.

For example, do not change:

```text
slice-28-cicd
```

to:

```text
slice-28-ci
slice28
cicd-28
ci-cd
```

The official slice ID must remain consistent across the project.

---

# 13. One Slice = One Primary Development Stream

A contributor working on Slice 28 should normally use:

```text
SCRUM-12
    ↓
slice-28-cicd
    ↓
feature/scrum-12-slice-28-cicd
```

Do not mix Slice 28 and Slice 29 implementation in the same PR.

If Slice 29 work is required, use its own Jira issue, branch, commits, and PR.

Additional technical branches for the same Jira issue are permitted when necessary, provided they retain the Jira key and remain associated with the same work item.

---

# 14. Dependencies

When a slice depends on another slice, document the dependency in the PR.

Example:

```markdown
## Dependencies

- Depends on SCRUM-13 / Slice 29 for OCI deployment target.
- Depends on SCRUM-14 / Slice 30 for Vercel deployment target.
```

Do not implement another slice's work inside the current slice merely to remove the dependency.

---

# 15. CI/CD Naming

CI/CD configuration must belong to the appropriate infrastructure slice.

For Slice 28:

```text
SCRUM-12
slice-28-cicd
feature/scrum-12-slice-28-cicd
```

CI/CD files must not be added incidentally to unrelated feature slices.

---

# 16. Secrets and Environment Variables

Never place secret values in:

- commits
- branches
- PR titles
- PR descriptions
- source code
- documentation
- Jira comments

Use:

```text
.env.example
```

to document required variable names.

Actual values must be stored in the appropriate secret-management system.

---

# 17. Merge Requirements

A PR should be merged only when:

- Required CI checks pass.
- Required reviewer approval is present.
- Requested changes are resolved.
- Acceptance criteria are satisfied.
- No unauthorized secret/configuration changes are present.
- Required human review has occurred for sensitive changes.
- The PR is associated with the correct Jira issue.

After merge:

```text
GitHub PR → merged
        ↓
Jira issue → Done
```

provided the slice's acceptance criteria are satisfied.

---

# 18. Jira Closure Rule

Contributors must **not** manually mark a development issue `Done` merely because:

- implementation is complete,
- a branch has been created,
- a PR has been opened,
- CI is passing, or
- the PR has been approved.

The development issue reaches `Done` only after:

1. The corresponding PR is merged.
2. Required CI checks have passed.
3. Required review has occurred.
4. The slice acceptance criteria are satisfied.

The merge event is the normal development lifecycle-closing event.

---

# 19. Main Branch Protection

The `main` branch should enforce the project workflow rather than relying on naming alone.

Recommended controls:

- Pull request required.
- Required CI checks.
- Required reviewer approval.
- Direct pushes restricted.
- Force pushes restricted.
- Sensitive infrastructure changes require human review.
- Secrets must never be committed.

Naming conventions provide traceability.

Branch protection provides enforcement.

Both are required.

---

# 20. What Naming Can and Cannot Fix

### Naming fixes

- Jira-to-GitHub traceability.
- Identifying which slice a commit belongs to.
- Identifying which Jira issue a PR belongs to.
- Consistent team workflow.
- Easier automation.
- Easier auditing.
- Easier debugging of Jira/GitHub synchronization.

### Naming does NOT automatically fix

- Jira/GitHub connection.
- Jira Development panel synchronization.
- Jira status transitions.
- Reviewer synchronization.
- GitHub webhook delivery.
- Jira custom fields.
- GitHub branch protection.
- CI execution.
- Authentication or permissions.

Therefore, naming and integration must be implemented together.

---

# 21. VARIO Golden Standard

For a normal Slice implementation, the complete standard is:

```text
Jira:
SCRUM-12

Slice:
slice-28-cicd

Branch:
feature/scrum-12-slice-28-cicd

Commit:
SCRUM-12 slice-28-cicd: add pull request CI workflow

PR:
[SCRUM-12] slice-28-cicd: add pull request CI workflow

PR Body:
Jira: SCRUM-12
Slice: Slice 28 — CI/CD

GitHub:
CI → Review → Approval → Merge

Jira:
To Do → In Progress → In Review → Done
```

---

# 22. Final Traceability Rule

Every implementation must be possible to trace in both directions:

```text
Jira → GitHub

SCRUM-12
   ↓
Slice 28
   ↓
Branch
   ↓
Commits
   ↓
PR
   ↓
Review
   ↓
CI
   ↓
Merge
```

and:

```text
GitHub → Jira

PR / Commit / Branch
        ↓
     SCRUM-12
        ↓
Slice 28 — CI/CD
        ↓
Jira status / reviewer / development link
```

If an engineer cannot trace a GitHub change back to exactly one Jira work item, the change is not following the VARIO development convention.

---

# 23. Golden Rules

1. **Jira key everywhere possible.**
2. **Use the official slice ID everywhere.**
3. **Use the canonical uppercase Jira key in commits and PRs.**
4. **Use lowercase Jira keys in branch names.**
5. **One slice per primary development stream.**
6. **One Jira issue should normally have one primary branch.**
7. **Additional technical branches must retain the Jira key.**
8. **Every PR must contain the Jira key.**
9. **Every contributor-authored implementation commit must contain the Jira key and slice ID.**
10. **Automatically generated commits are exempt from the contributor commit format.**
11. **GitHub reviewer is authoritative.**
12. **Approval is not Done.**
13. **Merge is the event that closes the development lifecycle.**
14. **Do not manually mark development work Done before merge and acceptance-criteria completion.**
15. **Naming provides traceability; integration provides synchronization.**
16. **Branch protection provides enforcement.**
17. **Never commit secrets.**
18. **Do not mix unrelated slices.**
19. **Do not bypass the PR/review/CI workflow.**
20. **Keep Jira, GitHub, and project documentation consistent.**
