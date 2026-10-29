#!/usr/bin/env python3
"""Synchronize VARIO slice and linked audit-bug Jira issues from GitHub PR events.

Safety rules:
- A merged PR alone never closes linked bugs.
- A linked bug is resolved only when the PR contains a checked, bug-specific
  verification line with test evidence AND all checks on the PR head commit pass.
- A slice is marked Done only when it has linked bugs and every linked bug is Done.
- Missing Jira credentials on non-merge events is a notice; on a merge it is fatal.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")

ISSUE_KEY_RE = re.compile(r"\bSCRUM-\d+\b", re.IGNORECASE)
VERIFICATION_RE = re.compile(
    r"^\s*[-*]\s*\[x\]\s*(SCRUM-\d+)\s*(?:[-—:]\s*)?(.*)$",
    re.IGNORECASE,
)


class ApiError(RuntimeError):
    pass


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise ApiError(f"{method} {url} returned HTTP {exc.code}: {details[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise ApiError(f"Request failed for {url}: {exc}") from exc


def jira_headers() -> dict[str, str]:
    token = base64.b64encode(f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def jira_request(path: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return request_json(
        f"{JIRA_BASE_URL}/rest/api/3/{path.lstrip('/')}",
        method=method,
        headers=jira_headers(),
        payload=payload,
    )


def github_request(path: str) -> dict[str, Any]:
    return request_json(
        f"https://api.github.com/{path.lstrip('/')}",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def comment(issue_key: str, message: str) -> None:
    document = {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": message}]}],
    }
    jira_request(f"issue/{issue_key}/comment", method="POST", payload={"body": document})


def get_issue(issue_key: str) -> dict[str, Any]:
    return jira_request(
        f"issue/{urllib.parse.quote(issue_key)}?fields=summary,status,issuetype,issuelinks"
    )


def transition_to(issue_key: str, target_status: str) -> bool:
    issue = get_issue(issue_key)
    current = issue.get("fields", {}).get("status", {}).get("name", "")
    if current.casefold() == target_status.casefold():
        print(f"{issue_key}: already {target_status}")
        return True

    result = jira_request(f"issue/{issue_key}/transitions")
    candidates = [
        transition
        for transition in result.get("transitions", [])
        if transition.get("to", {}).get("name", "").casefold() == target_status.casefold()
    ]
    if not candidates:
        print(f"NOTICE: no available Jira transition for {issue_key} -> {target_status}")
        return False

    jira_request(
        f"issue/{issue_key}/transitions",
        method="POST",
        payload={"transition": {"id": candidates[0]["id"]}},
    )
    print(f"{issue_key}: {current} -> {target_status}")
    return True


def linked_bug_keys(slice_key: str) -> list[str]:
    issue = get_issue(slice_key)
    links = issue.get("fields", {}).get("issuelinks", [])
    keys: set[str] = set()
    for link in links:
        for direction in ("inwardIssue", "outwardIssue"):
            linked = link.get(direction) or {}
            key = linked.get("key")
            if not key:
                continue
            linked_issue = get_issue(key)
            issue_type = linked_issue.get("fields", {}).get("issuetype", {}).get("name", "")
            if issue_type.casefold() == "bug":
                keys.add(key.upper())
    return sorted(keys, key=lambda key: int(key.split("-")[1]))


def verification_evidence(pr_body: str) -> dict[str, str]:
    """Return only checked bug lines that explicitly include test evidence."""
    evidence: dict[str, str] = {}
    for line in (pr_body or "").splitlines():
        match = VERIFICATION_RE.match(line)
        if not match:
            continue
        key, details = match.group(1).upper(), match.group(2).strip()
        if re.search(r"\b(test|tests|pytest|jest|playwright|verified by)\s*[:=]", details, re.I):
            if len(details) >= 12:
                evidence[key] = details
    return evidence


def checks_pass(head_sha: str) -> tuple[bool, str]:
    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return False, "GitHub token/repository context is missing"
    runs = github_request(
        f"repos/{GITHUB_REPOSITORY}/commits/{head_sha}/check-runs?per_page=100"
    ).get("check_runs", [])
    relevant = [
        run for run in runs
        if "jira bug sync" not in run.get("name", "").casefold()
        and "jira-bug-sync" not in run.get("name", "").casefold()
    ]
    if not relevant:
        return False, "no CI check runs were found for the PR head commit"
    pending = [run.get("name", "unnamed check") for run in relevant if run.get("status") != "completed"]
    failed = [
        f"{run.get('name', 'unnamed check')}={run.get('conclusion')}"
        for run in relevant
        if run.get("status") == "completed" and run.get("conclusion") != "success"
    ]
    if pending or failed:
        details = []
        if pending:
            details.append("pending: " + ", ".join(pending))
        if failed:
            details.append("not successful: " + ", ".join(failed))
        return False, "; ".join(details)
    return True, f"{len(relevant)} check runs completed successfully"


def issue_key_from_pr(title: str, body: str) -> str | None:
    # Prefer the key in the title to avoid accidentally selecting a bug key in the body.
    match = ISSUE_KEY_RE.search(title or "")
    if not match:
        match = ISSUE_KEY_RE.search(body or "")
    return match.group(0).upper() if match else None


def main() -> int:
    event_path = os.getenv("GITHUB_EVENT_PATH", "")
    if not event_path:
        print("GITHUB_EVENT_PATH is required", file=sys.stderr)
        return 1
    with open(event_path, encoding="utf-8") as event_file:
        event = json.load(event_file)

    pr = event.get("pull_request") or {}
    action = event.get("action", "")
    merged = bool(pr.get("merged"))
    title = pr.get("title", "")
    body = pr.get("body") or ""
    pr_url = pr.get("html_url", "")
    head_sha = (pr.get("head") or {}).get("sha", "")
    slice_key = issue_key_from_pr(title, body)

    if not slice_key:
        print("NOTICE: PR title/body has no SCRUM issue key; Jira sync skipped.")
        return 0
    if not JIRA_BASE_URL or not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
        message = "Jira credentials missing. Configure JIRA_BASE_URL, JIRA_USER_EMAIL, and JIRA_API_TOKEN repository secrets."
        if merged:
            print(message, file=sys.stderr)
            return 1
        print(f"NOTICE: {message} Jira status sync skipped for this non-merge event.")
        return 0

    try:
        if action != "closed":
            if pr.get("draft"):
                print("Draft PR: leaving Jira status unchanged.")
                return 0
            transition_to(slice_key, "In Review")
            return 0

        if not merged:
            transition_to(slice_key, "In Progress")
            return 0

        passed, check_summary = checks_pass(head_sha)
        if not passed:
            comment(slice_key, f"Jira automation did not resolve linked bugs for {pr_url}: CI verification gate failed ({check_summary}). Fix/check the CI state and rerun the workflow.")
            print(f"CI gate failed: {check_summary}", file=sys.stderr)
            return 1

        bugs = linked_bug_keys(slice_key)
        if not bugs:
            comment(slice_key, f"PR merged: {pr_url}. No linked Jira Bug issues were found, so automatic slice completion was withheld.")
            print(f"{slice_key}: no linked bugs; refusing automatic Done.")
            return 0

        evidence = verification_evidence(body)
        resolved: list[str] = []
        pending: list[str] = []
        for bug_key in bugs:
            bug = get_issue(bug_key)
            current = bug.get("fields", {}).get("status", {}).get("name", "")
            if current.casefold() == "done":
                resolved.append(bug_key)
                continue
            if bug_key not in evidence:
                pending.append(bug_key)
                continue
            if transition_to(bug_key, "Done"):
                comment(
                    bug_key,
                    f"Verified through merged PR {pr_url}. Evidence: {evidence[bug_key]}. CI gate: {check_summary}. Merge commit: {head_sha}.",
                )
                resolved.append(bug_key)
            else:
                pending.append(bug_key)

        latest_bugs = [get_issue(key) for key in bugs]
        all_done = all(
            item.get("fields", {}).get("status", {}).get("name", "").casefold() == "done"
            for item in latest_bugs
        )
        if all_done:
            transition_to(slice_key, "Done")
            comment(slice_key, f"All {len(bugs)} linked bugs are Done after merged PR {pr_url}. CI gate: {check_summary}.")
        else:
            transition_to(slice_key, "In Progress")
            comment(
                slice_key,
                f"PR merged: {pr_url}. CI gate passed ({check_summary}). Bugs resolved by this PR: {', '.join(resolved) or 'none'}. "
                f"Still open or lacking bug-specific verification evidence: {', '.join(pending) or 'check Jira statuses'}. "
                "Slice remains In Progress until every linked bug is verified Done.",
            )
        return 0
    except (ApiError, OSError, ValueError, KeyError) as exc:
        print(f"Jira bug sync failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
