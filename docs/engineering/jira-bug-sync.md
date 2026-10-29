# Jira bug sync automation

This workflow synchronizes VARIO slice issues and their native Jira issue links when GitHub pull requests change state.

## Required repository secrets

Add these under **GitHub → V-A-R-I-O/vario → Settings → Secrets and variables → Actions → Repository secrets**:

- `JIRA_BASE_URL`: `https://vario-pes.atlassian.net`
- `JIRA_USER_EMAIL`: email for the Jira account used by the automation
- `JIRA_API_TOKEN`: an Atlassian API token for that account

The account needs permission to browse, comment on, and transition the relevant Jira issues. Do not put the token in source code, PR text, or Jira comments. The workflow uses the repository-provided `GITHUB_TOKEN` for read-only check-run inspection.

**Security note:** the Jira workflow uses `pull_request_target` and checks out only the trusted default branch before loading Jira credentials. Do not change it to check out or execute code from the pull-request head; that could expose the Jira API token to untrusted PR code. The regular CI workflow continues to test the PR branch without Jira credentials.

Until the Jira secrets are configured, non-merge events emit a notice and skip synchronization; a merged-PR event fails visibly rather than silently pretending that Jira was updated.

## PR title and verification checklist

Keep the slice Jira key in the PR title, following the repository naming convention, for example:

```text
[SCRUM-42] slice-32-rasa-contract-v2: clear session slots between workflows
```

For each linked bug that this PR actually fixes, add a checked verification line in the PR body. The line must name the relevant test or verification evidence:

```markdown
## Bug verification
- [x] SCRUM-51 — test: tests/test_sessions.py::test_slots_reset
- [x] SCRUM-52 — test: tests/test_gateway.py::test_role_pack_outage_keeps_message
- [ ] SCRUM-53 — not verified in this PR
```

Do not check a bug unless its specific acceptance criteria were verified. A test reference is an auditable assertion by the PR author; CI passing does not independently prove that the named test fully covers the issue.

## State transitions

- PR opened/reopened/updated and not draft: attempt to move the slice to **In Review**.
- PR closed without merge: attempt to return the slice to **In Progress**.
- PR merged: inspect the PR head commit's GitHub check runs. Every discovered check run must be complete and successful before any linked bug is resolved.
- Only linked Jira issues of type **Bug** with checked, evidence-bearing verification lines are eligible to move to **Done**.
- Bugs without evidence, or bugs whose Jira transition is unavailable, remain open.
- The slice moves to **Done** only when it has linked bugs and all linked bugs are already or newly **Done**. Otherwise it remains **In Progress** and receives a comment listing outstanding verification.
- Successful bug transitions receive a Jira comment with the PR URL, verification text, CI result summary, and head commit SHA.

The workflow intentionally does not close every bug merely because a slice PR was merged. Bugs fixed by multiple slices must remain open until the final required verification is supplied.

## Traceability source

Use Jira's native **Relates** issue links between each slice and the bugs assigned to it. Labels are useful for filtering, but the sync script does not use labels to infer relationships. The script reads issue links from Jira at run time.

## Manual follow-up

After adding the secrets, open a test PR for a non-production change or rerun the workflow on an existing PR to validate Jira permissions and available workflow transitions. GitHub Actions workflow runs and Jira issue comments provide the audit trail.
