"""CLI: devin-orchestrator plan '<spec-json>' [--explain] | schema <name>."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path

from devin_orchestrator import registry as plan_registry
from devin_orchestrator.planner import plan_task, plan_task_json

SCHEMA_NAMES = ("spec", "plan")


def _explain(spec_json: str) -> str:
    """Human-readable walkthrough of the plan decision (OR-2)."""
    try:
        spec = json.loads(spec_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid task spec JSON: {exc}") from exc
    plan = plan_task(spec)
    lines = [f"Plan: {plan.workers} worker(s), mode={plan.mode}"]
    if plan.nesting_blocked:
        lines.append("- this session is already inside a worker; nesting is forbidden")
    else:
        lines.append(f"- {plan.rationale}")
    if plan.profiles:
        lines.append(f"- profile(s): {', '.join(sorted(set(plan.profiles)))}")
    if plan.collect:
        lines.append("- collect=true: gather every worker result before reporting")
    for w in plan.warnings:
        lines.append(f"- warning: {w}")
    for c in plan.file_collisions:
        lines.append(f"- collision: units {c['units']} both touch {c['path']}")
    return "\n".join(lines)


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
    plan_p.add_argument(
        "--explain", action="store_true",
        help="print a human-readable decision walkthrough instead of JSON",
    )
    schema_p = sub.add_parser(
        "schema", help="print the JSON Schema for the spec or the plan")
    schema_p.add_argument("name", choices=SCHEMA_NAMES)
    rec_p = sub.add_parser(
        "record",
        help="OR-3: append a plan's outcome to the local plans.jsonl "
        "registry (local only — not telemetry)")
    rec_p.add_argument("plan", help="the plan JSON to record against")
    rec_p.add_argument("--outcome", required=True,
                       choices=plan_registry.OUTCOMES)
    rec_p.add_argument("--notes", default="")
    rec_p.add_argument("--registry", type=Path,
                       help="override plans.jsonl location")
    hist_p = sub.add_parser(
        "history",
        help="read the local plan registry (counts + records)")
    hist_p.add_argument("--registry", type=Path,
                        help="override plans.jsonl location")
    hist_p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "schema":
        name = (
            "spec.schema.json" if args.name == "spec" else "plan.schema.json"
        )
        text = files("devin_orchestrator").joinpath(name).read_text(
            encoding="utf-8")
        print(text, end="" if text.endswith("\n") else "\n")
        return 0

    if args.command == "record":
        reg = args.registry or plan_registry.default_registry_path()
        try:
            plan = json.loads(args.plan)
            rec = plan_registry.record(reg, plan, args.outcome, args.notes)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(rec.to_dict()))
        return 0

    if args.command == "history":
        reg = args.registry or plan_registry.default_registry_path()
        summary = plan_registry.summarize(reg)
        if args.json:
            summary["records"] = list(plan_registry.iter_records(reg))
            print(json.dumps(summary, indent=2))
        else:
            print(f"{summary['total']} recorded plan(s): "
                  + ", ".join(f"{k}={v}" for k, v in
                              sorted(summary["by_outcome"].items())
                              ) if summary["by_outcome"] else "none")
            print(f"({summary['note']})")
        return 0

    raw = args.spec if args.spec is not None else args.spec_file.read_text(
        encoding="utf-8")
    try:
        out = _explain(raw) if args.explain else plan_task_json(raw)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
