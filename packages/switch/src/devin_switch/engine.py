"""The write path — snapshot, verify, apply, rollback.

Order of operations for ``use <profile> --apply``:

1. snapshot every managed file the profile will change into
   ``.devin-ecosystem/switch-backups/<ts>/`` (files that do not exist yet
   are recorded as ``existed: false`` in the manifest — nothing copied);
2. verify sha256 of every backup copy against both the recorded hash and
   the live source — refuse to write anything on mismatch;
3. write the overlay atomically (sibling tmp file + ``os.replace``);
4. append the journal entry.

``credentials.toml`` is excluded upstream (``plan`` marks it ``skip``) and
never reaches this module's file loops.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from devin_switch import journal
from devin_switch.paths import Roots
from devin_switch.plan import FilePlan

MANIFEST_NAME = "manifest.json"


class SnapshotError(Exception):
    """Snapshot verification failed — nothing was applied."""

    def __init__(self, problems: list[str], backup_dir: Path):
        self.problems = problems
        self.backup_dir = backup_dir
        super().__init__("; ".join(problems))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(target: Path, data: bytes) -> None:
    """Write via a sibling tmp file + ``os.replace`` (same-dir rename is
    atomic on POSIX and Windows)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".devin-switch.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)


def _unique_backup_dir(roots: Roots, stamp: str) -> Path:
    base = roots.backups_dir / stamp
    candidate, i = base, 1
    while candidate.exists():
        i += 1
        candidate = Path(f"{base}-{i}")
    return candidate


@dataclass
class ApplyResult:
    profile: str
    files_changed: list[str]
    backup_dir: Path | None
    journal_entry: dict[str, Any] | None
    skipped: list[str]


def snapshot(
    plans: list[FilePlan], backup_dir: Path, roots: Roots
) -> dict[str, Any]:
    """Copy the pre-switch bytes of every file about to change.

    The manifest records, per managed file: the profile-relative path, the
    absolute target, whether it existed and its sha256 (when it did).
    """
    backup_dir.mkdir(parents=True, exist_ok=False)
    files: list[dict[str, Any]] = []
    for fp in plans:
        if not fp.needs_write:
            continue
        record: dict[str, Any] = {
            "rel": fp.rel,
            "target": str(fp.target),
            "existed": fp.old_bytes is not None,
            "sha256": None,
        }
        if fp.old_bytes is not None:
            dest = backup_dir / fp.rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp.target, dest)
            record["sha256"] = sha256_file(dest)
        files.append(record)
    manifest = {
        "version": 1,
        "files": files,
    }
    (backup_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


def verify_snapshot(manifest: dict[str, Any], backup_dir: Path) -> list[str]:
    """Every backup copy must hash to its recorded sha256 AND still match
    the live source file (which could have changed mid-switch)."""
    problems: list[str] = []
    for record in manifest.get("files", []):
        if not record.get("existed"):
            continue
        rel, recorded = record["rel"], record["sha256"]
        copy = backup_dir / rel
        if not copy.is_file():
            problems.append(f"{rel}: backup copy missing")
            continue
        if sha256_file(copy) != recorded:
            problems.append(f"{rel}: backup copy sha256 mismatch")
            continue
        source = Path(record["target"])
        if not source.is_file() or sha256_file(source) != recorded:
            problems.append(
                f"{rel}: source changed between snapshot and verify"
            )
    return problems


def apply_plan(
    profile_name: str, plans: list[FilePlan], roots: Roots
) -> ApplyResult:
    """Snapshot → verify → write → journal. Raises ``SnapshotError``
    before any file is written when verification fails."""
    changed = [fp for fp in plans if fp.needs_write]
    skipped = [fp.rel for fp in plans if fp.action == "skip"]
    if not changed:
        entry = journal.append(
            roots.journal_path, "use", profile_name, [], None
        )
        return ApplyResult(profile_name, [], None, entry, skipped)

    backup_dir = _unique_backup_dir(roots, journal.backup_stamp())
    manifest = snapshot(changed, backup_dir, roots)
    problems = verify_snapshot(manifest, backup_dir)
    if problems:
        # Leave the backup dir in place — it is the evidence of what the
        # files looked like when the switch was attempted.
        raise SnapshotError(problems, backup_dir)

    for fp in changed:
        atomic_write(fp.target, fp.new_bytes)

    files_changed = [fp.rel for fp in changed]
    entry = journal.append(
        roots.journal_path, "use", profile_name, files_changed, backup_dir
    )
    return ApplyResult(profile_name, files_changed, backup_dir, entry, skipped)


# ---------------------------------------------------------------------------
# rollback
# ---------------------------------------------------------------------------


@dataclass
class RollbackStep:
    rel: str
    target: Path
    action: str  # "restore" | "delete"
    backup_copy: Path | None


@dataclass
class RollbackResult:
    profile: str
    steps: list[RollbackStep]
    journal_entry: dict[str, Any]


def _load_manifest(backup_dir: Path) -> dict[str, Any]:
    manifest_path = backup_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"backup manifest missing: {manifest_path}"
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def plan_rollback(entry: dict[str, Any], roots: Roots) -> list[RollbackStep]:
    """Steps to undo a ``use`` entry: restore files that existed, delete
    files the switch created."""
    backup_dir = Path(entry["backup_dir"])
    manifest = _load_manifest(backup_dir)
    steps: list[RollbackStep] = []
    for record in manifest.get("files", []):
        rel = record["rel"]
        target = Path(record["target"])
        if record["existed"]:
            copy = backup_dir / rel
            expected = record.get("sha256")
            if not copy.is_file():
                raise FileNotFoundError(
                    f"backup copy missing for {rel}: {copy}"
                )
            if expected and sha256_file(copy) != expected:
                raise SnapshotError(
                    [(f"{rel}: backup copy sha256 mismatch — refusing to "
                      "restore a corrupted snapshot")],
                    backup_dir,
                )
            steps.append(RollbackStep(rel, target, "restore", copy))
        else:
            steps.append(RollbackStep(rel, target, "delete", None))
    return steps


def _prune_empty_dirs(path: Path, stop_at: Path) -> None:
    path = path.parent
    while path != stop_at and stop_at in path.parents:
        try:
            path.rmdir()
        except OSError:
            break
        path = path.parent


def apply_rollback(
    entry: dict[str, Any], steps: list[RollbackStep], roots: Roots
) -> RollbackResult:
    for step in steps:
        if step.action == "restore":
            assert step.backup_copy is not None
            atomic_write(step.target, step.backup_copy.read_bytes())
        else:
            if step.target.is_file():
                step.target.unlink()
            _prune_empty_dirs(step.target, roots.data_dir)
            _prune_empty_dirs(step.target, roots.config_dir)
    files_changed = [s.rel for s in steps]
    entry_out = journal.append(
        roots.journal_path,
        "rollback",
        str(entry.get("profile", "")),
        files_changed,
        None,
    )
    return RollbackResult(
        str(entry.get("profile", "")), steps, entry_out
    )
