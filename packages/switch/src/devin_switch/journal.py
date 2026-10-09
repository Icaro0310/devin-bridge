"""Append-only switch journal: ``.devin-ecosystem/switch-journal.jsonl``.

One JSON object per line: ``{ts, action, profile, files_changed,
backup_dir}``. ``action`` is ``"use"`` for profile switches (carries the
snapshot dir) or ``"rollback"`` for restores (``backup_dir`` is null —
rolling back does not consume the backup, it stays for re-``use``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def journal_timestamp(dt: datetime | None = None) -> str:
    dt = dt or utc_now()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def backup_stamp(dt: datetime | None = None) -> str:
    dt = dt or utc_now()
    return dt.strftime("%Y%m%dT%H%M%SZ")


def append(
    journal_path: Path,
    action: str,
    profile: str,
    files_changed: list[str],
    backup_dir: Path | None,
    when: datetime | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ts": journal_timestamp(when),
        "action": action,
        "profile": profile,
        "files_changed": list(files_changed),
        "backup_dir": str(backup_dir) if backup_dir is not None else None,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_all(journal_path: Path) -> list[dict[str, Any]]:
    """Parse the journal; corrupt lines are skipped, never fatal."""
    entries: list[dict[str, Any]] = []
    if not journal_path.is_file():
        return entries
    try:
        text = journal_path.read_text(encoding="utf-8")
    except OSError:
        return entries
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            entries.append(obj)
    return entries


def last_use_entry(journal_path: Path) -> dict[str, Any] | None:
    """Most recent ``use`` entry that still has its backup directory."""
    for entry in reversed(read_all(journal_path)):
        if entry.get("action") != "use":
            continue
        backup = entry.get("backup_dir")
        if backup and Path(backup).is_dir():
            return entry
    return None
