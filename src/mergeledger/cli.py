"""Command-line interface for mergeledger."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone

from .github import refresh_item
from .model import LedgerError, audit_ledger, require_valid_ledger
from .render import render_cards


def load_ledger(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_ledger(path: pathlib.Path, ledger: dict) -> None:
    path.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def command_audit(args: argparse.Namespace) -> int:
    findings = audit_ledger(load_ledger(args.ledger))
    if findings:
        for finding in findings:
            print(f"ERROR {finding}")
        return 1
    print("OK ledger is valid and privacy-safe")
    return 0


def command_render(args: argparse.Namespace) -> int:
    ledger = load_ledger(args.ledger)
    require_valid_ledger(ledger)
    rendered = render_cards(ledger["items"]) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    ledger = load_ledger(args.ledger)
    for index, item in enumerate(ledger.get("items", [])):
        ledger["items"][index] = refresh_item(item)
    ledger["refreshed_at"] = datetime.now(timezone.utc).isoformat()
    require_valid_ledger(ledger)
    write_ledger(args.ledger, ledger)
    print(f"OK refreshed {len(ledger['items'])} contribution(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mergeledger",
        description="Audit, refresh, and render evidence-led contribution records.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="validate claims and privacy boundaries")
    audit.add_argument("ledger", type=pathlib.Path)
    audit.set_defaults(handler=command_audit)

    render = subparsers.add_parser("render", help="render Markdown contribution cards")
    render.add_argument("ledger", type=pathlib.Path)
    render.add_argument("--output", "-o", type=pathlib.Path)
    render.set_defaults(handler=command_render)

    refresh = subparsers.add_parser("refresh", help="refresh states from GitHub")
    refresh.add_argument("ledger", type=pathlib.Path)
    refresh.set_defaults(handler=command_refresh)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.handler(args))
    except (LedgerError, json.JSONDecodeError, OSError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
