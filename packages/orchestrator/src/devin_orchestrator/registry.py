"""OR-3: local plan registry — plan vs. outcome, on disk only.

Not telemetry: nothing leaves the machine. ``record`` appends a plan hash
plus its outcome to a JSONL log; ``history`` reads it back so future plans
can be compared against what actually happened. The registry lives under
the ecosystem config dir by default and is human-readable throughout.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

OUTCOMES = ("success", "partial", "failed", "aborted")


def default_registry_path() -> Path:
    """``<config>/.devin-ecosystem/plans.jsonl`` — same root the hook
    dispatcher and scheduler already share."""
    override = os.environ.get("DEVIN_ECOSYSTEM_CONFIG_DIR")
    if override:
        return Path(override).expanduser() / "plans.jsonl"
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return base / "devin-ecosystem" / "plans.jsonl"
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / ".devin-ecosystem" / "plans.jsonl"


def _plan_hash(plan: dict[str, Any]) -> str:
    blob = json.dumps(plan, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class PlanRecord:
    ts: float
    plan_hash: str
    workers: int
    mode: str | None
    outcome: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "plan_hash": self.plan_hash,
            "workers": self.workers,
            "mode": self.mode,
            "outcome": self.outcome,
            "notes": self.notes,
        }


def record(registry: Path, plan: dict[str, Any], outcome: str,
           notes: str = "") -> PlanRecord:
    """Append one outcome to the JSONL registry (atomic-ish: single write)."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    rec = PlanRecord(
        ts=time.time(),
        plan_hash=_plan_hash(plan),
        workers=len(plan.get("workers", []))
        if isinstance(plan.get("workers"), list)
        else int(plan.get("workers", 0) or 0),
        mode=plan.get("mode"),
        outcome=outcome,
        notes=notes,
    )
    registry.parent.mkdir(parents=True, exist_ok=True)
    with open(registry, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec.to_dict(), separators=(",", ":")) + "\n")
    return rec


def iter_records(registry: Path) -> Iterator[dict[str, Any]]:
    if not registry.is_file():
        return
    for line in registry.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def summarize(registry: Path) -> dict[str, Any]:
    recs = list(iter_records(registry))
    by_outcome: dict[str, int] = {}
    for r in recs:
        by_outcome[r["outcome"]] = by_outcome.get(r["outcome"], 0) + 1
    return {
        "registry": str(registry),
        "total": len(recs),
        "by_outcome": by_outcome,
        "note": "local registry only — nothing leaves the machine",
    }
