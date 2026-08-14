"""Validation and claim gates for contribution evidence."""

from __future__ import annotations

import re
from collections.abc import Iterable


ALLOWED_STATES = {"prepared", "submitted", "under_review", "merged", "closed"}
REQUIRED_FIELDS = {
    "owner",
    "repo",
    "number",
    "theme",
    "stack",
    "change",
    "verification",
    "state",
}
PRIVATE_KEYS = {
    "company",
    "employer",
    "school",
    "education",
    "location",
    "email",
    "legal_name",
    "phone",
}
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)


class LedgerError(ValueError):
    """Raised when a ledger cannot support its public claims."""


def _walk(value: object, path: str = "$") -> Iterable[tuple[str, object]]:
    yield path, value
    if isinstance(value, dict):
        for key, nested in value.items():
            yield from _walk(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _walk(nested, f"{path}[{index}]")


def audit_privacy(ledger: dict) -> list[str]:
    """Return privacy findings without mutating the ledger."""
    findings: list[str] = []
    for path, value in _walk(ledger):
        key = path.rsplit(".", 1)[-1].lower()
        if key in PRIVATE_KEYS and value not in (None, "", [], {}):
            findings.append(f"{path}: private identity field is not allowed")
        if isinstance(value, str) and EMAIL_PATTERN.search(value):
            findings.append(f"{path}: email address detected")
    return findings


def validate_item(item: dict, index: int) -> list[str]:
    findings: list[str] = []
    missing = sorted(REQUIRED_FIELDS - item.keys())
    if missing:
        findings.append(f"items[{index}]: missing fields: {', '.join(missing)}")
        return findings

    state = item["state"]
    if state not in ALLOWED_STATES:
        findings.append(f"items[{index}].state: unsupported state {state!r}")
    if state == "merged" and not item.get("merged_at"):
        findings.append(
            f"items[{index}]: merged claim requires authoritative merged_at evidence"
        )
    if state != "merged" and item.get("merged_at"):
        findings.append(
            f"items[{index}]: merged_at is present but state is {state!r}"
        )
    if not isinstance(item["number"], int) or item["number"] <= 0:
        findings.append(f"items[{index}].number: expected a positive integer")
    return findings


def audit_ledger(ledger: dict) -> list[str]:
    findings = audit_privacy(ledger)
    if ledger.get("schema_version") != 1:
        findings.append("schema_version: only version 1 is supported")
    items = ledger.get("items")
    if not isinstance(items, list):
        findings.append("items: expected a list")
        return findings
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            findings.append(f"items[{index}]: expected an object")
            continue
        findings.extend(validate_item(item, index))
    return findings


def require_valid_ledger(ledger: dict) -> None:
    findings = audit_ledger(ledger)
    if findings:
        raise LedgerError("\n".join(findings))
