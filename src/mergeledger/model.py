"""Validation and claim gates for contribution evidence."""

from __future__ import annotations

import os
import pathlib
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
PHONE_PATTERN = re.compile(r"(?<![\w.])\+?\d[\d\s().-]{7,}\d(?![\w.])")
# Timestamps, dates and versions are digit-dense and would otherwise read as phone
# numbers. A privacy check that fires on every refreshed_at trains the reader to
# ignore it, so strip these before scanning.
TIMESTAMPLIKE_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?"
    r"|\bv?\d+\.\d+(?:\.\d+)+\b"
)


def looks_like_phone(value: str) -> bool:
    """True when a string carries a phone number rather than a timestamp."""
    return bool(PHONE_PATTERN.search(TIMESTAMPLIKE_PATTERN.sub(" ", value)))


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


def load_private_terms(source: str | None = None) -> list[str]:
    """Terms that must never appear in a public ledger -- employer, school, city,
    internal project names.

    Deliberately not read from the ledger: the ledger is the artifact that gets
    published, so a list of private terms stored inside it would leak exactly what
    it is meant to protect. Supply them from a local file kept out of version
    control, or from ``MERGELEDGER_PRIVATE_TERMS`` as a newline- or
    comma-separated value.
    """
    raw = ""
    if source:
        raw = pathlib.Path(source).read_text(encoding="utf-8")
    else:
        raw = os.environ.get("MERGELEDGER_PRIVATE_TERMS", "")
    terms = []
    for chunk in raw.replace(",", "\n").splitlines():
        term = chunk.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return terms


def audit_privacy(ledger: dict, private_terms: Iterable[str] = ()) -> list[str]:
    """Return privacy findings without mutating the ledger.

    Structured keys and obvious patterns are only part of the risk. In practice a
    leak arrives inside free text -- an employer named in a change description, a
    city in a note -- so declared private terms are matched there too.
    """
    findings: list[str] = []
    terms = [t for t in private_terms if t]
    for path, value in _walk(ledger):
        key = path.rsplit(".", 1)[-1].lower()
        if key in PRIVATE_KEYS and value not in (None, "", [], {}):
            findings.append(f"{path}: private identity field is not allowed")
        if key == "private_terms":
            findings.append(
                f"{path}: private terms must not be stored in the ledger; "
                "keep them in a local file or MERGELEDGER_PRIVATE_TERMS"
            )
        if not isinstance(value, str):
            continue
        if EMAIL_PATTERN.search(value):
            findings.append(f"{path}: email address detected")
        if looks_like_phone(value):
            findings.append(f"{path}: phone number detected")
        lowered = value.lower()
        for term in terms:
            if term.lower() in lowered:
                findings.append(f"{path}: private term {term!r} detected")
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


def audit_ledger(ledger: dict, private_terms: Iterable[str] = ()) -> list[str]:
    findings = audit_privacy(ledger, private_terms)
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


# Ordered by how strong a public claim each state makes. A recorded state that
# outranks the upstream evidence is an overstatement, which is the failure this
# project exists to prevent.
STATE_STRENGTH = {"prepared": 0, "submitted": 1, "under_review": 2, "merged": 3}


def compare_claim(item: dict, upstream_state: str, upstream_merged_at: str | None, index: int) -> list[str]:
    """Findings where a recorded claim is not supported by upstream evidence.

    Structural validation only checks that a ``merged`` claim carries a
    ``merged_at`` value -- but that value is written by the ledger's author, so
    on its own it proves nothing. This compares the claim to the live state.
    """
    findings: list[str] = []
    claimed = item.get("state")
    ref = f"items[{index}] {item.get('owner')}/{item.get('repo')}#{item.get('number')}"

    if upstream_state == "closed":
        if claimed == "merged":
            findings.append(f"{ref}: claims merged but the pull request was closed without merging")
        elif claimed != "closed":
            findings.append(f"{ref}: claims {claimed!r} but the pull request is closed")
        return findings

    claimed_rank = STATE_STRENGTH.get(claimed)
    upstream_rank = STATE_STRENGTH.get(upstream_state)
    if claimed_rank is None or upstream_rank is None:
        return findings

    if claimed_rank > upstream_rank:
        findings.append(
            f"{ref}: claims {claimed!r} but upstream evidence supports only {upstream_state!r}"
        )
    elif claimed_rank < upstream_rank:
        findings.append(
            f"{ref}: recorded as {claimed!r} but upstream is already {upstream_state!r}; refresh the ledger"
        )

    if claimed == "merged":
        recorded_merged_at = item.get("merged_at")
        if not upstream_merged_at:
            findings.append(f"{ref}: merged claim has no upstream merged_at")
        elif recorded_merged_at and recorded_merged_at != upstream_merged_at:
            findings.append(
                f"{ref}: merged_at {recorded_merged_at!r} does not match upstream {upstream_merged_at!r}"
            )
    return findings


def verify_ledger(ledger: dict, resolve) -> list[str]:
    """Check every claim against upstream. ``resolve(item)`` returns
    ``(state, merged_at)`` so this stays testable without network access."""
    findings: list[str] = []
    for index, item in enumerate(ledger.get("items") or []):
        if not isinstance(item, dict):
            continue
        try:
            upstream_state, upstream_merged_at = resolve(item)
        except Exception as error:  # noqa: BLE001 - surfaced as a finding, not a crash
            findings.append(
                f"items[{index}] {item.get('owner')}/{item.get('repo')}#{item.get('number')}: "
                f"could not verify against upstream: {error}"
            )
            continue
        findings.extend(compare_claim(item, upstream_state, upstream_merged_at, index))
    return findings


def require_valid_ledger(ledger: dict) -> None:
    findings = audit_ledger(ledger)
    if findings:
        raise LedgerError("\n".join(findings))
