"""Markdown rendering for evidence-led public profiles."""

from __future__ import annotations


STATE_LABELS = {
    "prepared": "Prepared locally",
    "submitted": "Submitted",
    "under_review": "Under review",
    "merged": "Merged",
    "closed": "Closed",
}


def issue_slug(item: dict) -> str:
    """Repository the tracking issue lives in.

    Defaults to the pull request's repository, but many projects split code and
    issues across repositories. Getting this wrong does not produce a dead link:
    GitHub resolves ``/issues/N`` to ``/pull/N`` when that number is a pull
    request in the repository, so the evidence link silently points at an
    unrelated document instead.
    """
    owner = item.get("issue_owner") or item["owner"]
    repo = item.get("issue_repo") or item["repo"]
    return f"{owner}/{repo}"


def evidence_links(item: dict) -> str:
    base = f"https://github.com/{item['owner']}/{item['repo']}"
    links: list[str] = []
    if issue_number := item.get("issue_number"):
        issue_base = f"https://github.com/{issue_slug(item)}"
        links.append(f"[Issue #{issue_number}]({issue_base}/issues/{issue_number})")
    links.append(f"[PR #{item['number']}]({base}/pull/{item['number']})")
    links.append(item["verification"])
    return " · ".join(links)


def render_cards(items: list[dict]) -> str:
    cards: list[str] = []
    for index, item in enumerate(items, start=1):
        repo_url = f"https://github.com/{item['owner']}/{item['repo']}"
        cards.append(
            "\n".join(
                [
                    f"### `{index:02d}` · [`{item['owner']}/{item['repo']}`]({repo_url})",
                    "",
                    f"**{item['theme']}** · `{item['stack']}` · **{STATE_LABELS[item['state']]}**",
                    "",
                    item["change"],
                    "",
                    f"Evidence → {evidence_links(item)}",
                ]
            )
        )
    return "\n\n---\n\n".join(cards)
