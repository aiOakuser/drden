#!/usr/bin/env python3
"""Utility to delete stale Git branches via the GitHub API.

The script is intended to run inside GitHub Actions where ``GITHUB_TOKEN`` and
``GITHUB_REPOSITORY`` are automatically provided. Branches are deleted when they
meet all of the following criteria:

- Not protected and not named in ``PROTECTED_BRANCHES``
- Do not match patterns in ``PROTECTED_PATTERNS`` (``fnmatch`` syntax)
- Not associated with an open pull request
- Last commit is older than ``BRANCH_STALE_DAYS``

Environment variables (all optional):

``DRY_RUN``
    When set to ``true`` (case-insensitive) no delete requests are issued.

``BRANCH_STALE_DAYS``
    Age threshold in days before a branch becomes a deletion candidate.
    Defaults to 45.

``BRANCH_DELETE_LIMIT``
    Maximum number of branches to delete per run. Defaults to 10.

``PROTECTED_BRANCHES``
    Comma-separated list of branch names that should never be removed in
    addition to the repository's default branch. Defaults to
    "main,master,production,staging,develop".

``PROTECTED_PATTERNS``
    Comma-separated wildcard patterns that should be ignored (e.g.,
    ``release/*``). Defaults to "release/*,hotfix/*,dependabot/*,renovate/*".
"""

from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

API_ROOT = "https://api.github.com"
DEFAULT_PROTECTED_BRANCHES = {"main", "master", "production", "staging", "develop"}
DEFAULT_PROTECTED_PATTERNS = {"release/*", "hotfix/*", "dependabot/*", "renovate/*"}


@dataclass(slots=True)
class Branch:
    name: str
    sha: str
    protected: bool
    committed_at: dt.datetime | None

    @property
    def age_days(self) -> float:
        if not self.committed_at:
            return float("inf")  # Treat missing timestamps as very old
        delta = dt.datetime.now(dt.timezone.utc) - self.committed_at
        return delta.total_seconds() / 86400


class GitHubClient:
    def __init__(self, token: str, repository: str) -> None:
        self.token = token
        self.repository = repository
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "branch-cleanup-script",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        data: bytes | None = None,
    ) -> tuple[dict[str, str], bytes]:
        url = f"{API_ROOT}{path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        request = urllib.request.Request(url, headers=self.headers, method=method)
        if data is not None:
            request.data = data

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                return dict(response.headers.items()), body
        except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in workflow
            message = exc.read().decode("utf-8", errors="ignore")
            print(f"GitHub API error ({exc.code}) when calling {path}: {message}", file=sys.stderr)
            raise
        except urllib.error.URLError as exc:  # pragma: no cover - exercised in workflow
            print(f"Failed to reach GitHub API: {exc}", file=sys.stderr)
            raise

    def get_json(self, path: str, *, params: dict[str, str | int] | None = None) -> object:
        _, body = self._request("GET", path, params=params)
        return json.loads(body.decode("utf-8"))

    def delete(self, path: str) -> None:
        self._request("DELETE", path)

    # Convenience helpers -------------------------------------------------
    def fetch_repository(self) -> dict:
        return self.get_json(f"/repos/{self.repository}")

    def iter_branches(self) -> list[Branch]:
        branches: list[Branch] = []
        page = 1
        per_page = 100
        while True:
            payload = self.get_json(
                f"/repos/{self.repository}/branches",
                params={"per_page": per_page, "page": page},
            )
            if not isinstance(payload, list):
                break
            for entry in payload:
                commit_data = (entry.get("commit") or {}).get("commit") or {}
                committed_at = commit_data.get("committer", {}).get("date") or commit_data.get("author", {}).get("date")
                branches.append(
                    Branch(
                        name=entry.get("name", ""),
                        sha=(entry.get("commit") or {}).get("sha", ""),
                        protected=bool(entry.get("protected")),
                        committed_at=_parse_iso8601(committed_at),
                    )
                )
            if len(payload) < per_page:
                break
            page += 1
        return branches

    def fetch_open_pr_branch_names(self) -> set[str]:
        open_branches: set[str] = set()
        page = 1
        per_page = 100
        while True:
            payload = self.get_json(
                f"/repos/{self.repository}/pulls",
                params={"state": "open", "per_page": per_page, "page": page},
            )
            if not isinstance(payload, list) or not payload:
                break
            for pr in payload:
                head = pr.get("head") or {}
                ref = head.get("ref") or ""
                if ref:
                    open_branches.add(ref)
            if len(payload) < per_page:
                break
            page += 1
        return open_branches

    def delete_branch(self, name: str) -> None:
        encoded = urllib.parse.quote(name, safe="")
        self.delete(f"/repos/{self.repository}/git/refs/heads/{encoded}")


def _parse_iso8601(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return dt.datetime.fromisoformat(normalized).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def _load_env_set(name: str, default: set[str]) -> set[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return set(default)
    return {item.strip() for item in raw.split(",") if item.strip()}


def _boolean_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _matches_pattern(name: str, patterns: set[str]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def main() -> int:
    token = os.getenv("GITHUB_TOKEN")
    repository = os.getenv("GITHUB_REPOSITORY")
    if not token or not repository:
        print("GITHUB_TOKEN and GITHUB_REPOSITORY must be set.", file=sys.stderr)
        return 1

    dry_run = _boolean_env("DRY_RUN", default=False)
    stale_days = max(1, _int_env("BRANCH_STALE_DAYS", 45))
    delete_limit = max(1, _int_env("BRANCH_DELETE_LIMIT", 10))
    protected_branches = _load_env_set("PROTECTED_BRANCHES", DEFAULT_PROTECTED_BRANCHES)
    protected_patterns = _load_env_set("PROTECTED_PATTERNS", DEFAULT_PROTECTED_PATTERNS)

    client = GitHubClient(token, repository)
    repo_info = client.fetch_repository()
    default_branch = repo_info.get("default_branch") or "main"
    protected_branches.add(default_branch)
    print(f"Repository: {repository}")
    print(f"Default branch: {default_branch}")
    print(f"Dry run: {'yes' if dry_run else 'no'}")
    print(f"Stale threshold: {stale_days} days")
    print(f"Delete limit: {delete_limit}")

    branches = client.iter_branches()
    print(f"Discovered {len(branches)} total branches")

    open_pr_branches = client.fetch_open_pr_branch_names()
    if open_pr_branches:
        print(f"Skipping {len(open_pr_branches)} branch(es) with open pull requests")

    candidates: list[Branch] = []
    for branch in branches:
        if not branch.name or branch.name in protected_branches:
            continue
        if branch.protected or _matches_pattern(branch.name, protected_patterns):
            continue
        if branch.name in open_pr_branches:
            continue
        if branch.age_days < stale_days:
            continue
        candidates.append(branch)

    if not candidates:
        print("No stale branches found.")
        return 0

    candidates.sort(key=lambda b: b.age_days, reverse=True)
    deletions = candidates[:delete_limit]

    print(f"Preparing to delete {len(deletions)} branch(es):")
    for branch in deletions:
        age = int(branch.age_days)
        committed = branch.committed_at.isoformat() if branch.committed_at else "unknown"
        print(f"  - {branch.name} (last commit: {committed}, ~{age}d old)")

    if dry_run:
        print("Dry run enabled; no branches were deleted.")
        return 0

    failures = 0
    for branch in deletions:
        try:
            client.delete_branch(branch.name)
            print(f"Deleted branch: {branch.name}")
        except urllib.error.HTTPError:
            failures += 1
        except urllib.error.URLError:
            failures += 1

    if failures:
        print(f"Completed with {failures} delete failure(s).", file=sys.stderr)
        return 1

    print("Branch cleanup completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
