"""CLI: devin-orchestrator plan '<spec-json>' [--spec-file path]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from devin_orchestrator.planner import plan_task_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="devin-orchestrator",
        description="Decide how many background workers a task should fan out to.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    plan_p = sub.add_parser("plan", help="emit a worker plan as JSON")
    group = plan_p.add_mutually_exclusive_group(required=True)
    group.add_argument("spec", nargs="?", help="task spec as a JSON string")
    group.add_argument("--spec-file", type=Path, help="path to a JSON task spec")
    args = parser.parse_args(argv)

    if args.command == "plan":
        raw = args.spec if args.spec is not None else args.spec_file.read_text(encoding="utf-8")
        try:
            print(plan_task_json(raw))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
