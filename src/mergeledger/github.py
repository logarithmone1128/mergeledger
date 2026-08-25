"""Small GitHub REST client used to refresh pull-request evidence."""

from __future__ import annotations

import json
import os
import urllib.request


def _get(path: str):
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
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


def fetch_pull_request(owner: str, repo: str, number: int) -> dict:
    return _get(f"repos/{owner}/{repo}/pulls/{number}")


def fetch_reviews(owner: str, repo: str, number: int) -> list:
    """Reviews left on a pull request. Empty when nobody has reviewed it yet."""
    reviews = _get(f"repos/{owner}/{repo}/pulls/{number}/reviews")
    return reviews if isinstance(reviews, list) else []


def normalized_state(pull_request: dict, reviews: list | None = None) -> str:
    """Map a pull request to a ledger state without overstating it.

    An open pull request is only ``under_review`` once there is evidence that
    review actually started: a submitted review, or a reviewer or team the
    maintainers asked for. An open pull request nobody has looked at is
    ``submitted`` -- which is the whole point of keeping the states apart. A
    draft is never ``under_review``, since it has not been offered for review.
    """
    if pull_request.get("merged_at"):
        return "merged"
    if pull_request.get("state") != "open":
        return "closed"
    if pull_request.get("draft"):
        return "submitted"
    requested = pull_request.get("requested_reviewers") or []
    requested_teams = pull_request.get("requested_teams") or []
    if (reviews or []) or requested or requested_teams:
        return "under_review"
    return "submitted"


def refresh_item(item: dict) -> dict:
    pull_request = fetch_pull_request(item["owner"], item["repo"], item["number"])
    reviews = []
    if pull_request.get("state") == "open" and not pull_request.get("draft"):
        reviews = fetch_reviews(item["owner"], item["repo"], item["number"])
    refreshed = dict(item)
    refreshed["state"] = normalized_state(pull_request, reviews)
    refreshed["merged_at"] = pull_request.get("merged_at")
    refreshed["updated_at"] = pull_request.get("updated_at")
    refreshed["html_url"] = pull_request.get("html_url")
    return refreshed
