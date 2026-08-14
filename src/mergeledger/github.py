"""Small GitHub REST client used to refresh pull-request evidence."""

from __future__ import annotations

import json
import os
import urllib.request


def fetch_pull_request(owner: str, repo: str, number: int) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "mergeledger/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def normalized_state(pull_request: dict) -> str:
    if pull_request.get("merged_at"):
        return "merged"
    if pull_request.get("state") == "open":
        return "under_review"
    return "closed"


def refresh_item(item: dict) -> dict:
    pull_request = fetch_pull_request(item["owner"], item["repo"], item["number"])
    refreshed = dict(item)
    refreshed["state"] = normalized_state(pull_request)
    refreshed["merged_at"] = pull_request.get("merged_at")
    refreshed["updated_at"] = pull_request.get("updated_at")
    refreshed["html_url"] = pull_request.get("html_url")
    return refreshed
