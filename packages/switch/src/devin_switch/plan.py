"""What ``use <profile>`` would do, per file — computed before anything
writes, and the source of both the dry-run diff and the apply step.

Actions: ``create`` (target absent), ``modify`` (bytes differ),
``unchanged`` (already matches), ``skip`` (never-managed file such as
``credentials.toml``).
"""

from __future__ import annotations

import difflib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from devin_switch.jsonc import try_load_json_bytes
from devin_switch.paths import Roots, target_for
from devin_switch.profiles import Profile
from devin_switch.redact import (
    display_value,
    is_credential_file,
    is_never_touch,
    mask_line,
)


@dataclass
class FilePlan:
    rel: str  # profile-relative posix path
    target: Path
    action: str  # create | modify | unchanged | skip
    old_bytes: bytes | None
    new_bytes: bytes
    skip_reason: str = ""

    @property
    def needs_write(self) -> bool:
        return self.action in ("create", "modify")


def build_plan(profile: Profile, roots: Roots) -> list[FilePlan]:
    plans: list[FilePlan] = []
    for rel in sorted(profile.files):
        try:
            target = target_for(rel, roots)
        except ValueError as exc:
            plans.append(
                FilePlan(rel, Path(rel), "skip", None, b"", str(exc))
            )
            continue
        if is_never_touch(rel):
            plans.append(
                FilePlan(
                    rel,
                    target,
                    "skip",
                    None,
                    b"",
                    "credentials.toml is never managed — "
                    "not read, not written",
                )
            )
            continue
        new_bytes = profile.file_bytes(rel)
        old_bytes = target.read_bytes() if target.is_file() else None
        if old_bytes is None:
            action = "create"
        elif old_bytes == new_bytes:
            action = "unchanged"
        else:
            action = "modify"
        plans.append(FilePlan(rel, target, action, old_bytes, new_bytes))
    return plans


# ---------------------------------------------------------------------------
# diffs
# ---------------------------------------------------------------------------


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested dicts/lists to ``a.b[0].c -> leaf`` pairs."""
    flat: dict[str, Any] = {}
    if isinstance(obj, dict):
        if not obj:
            flat[prefix or "."] = {}
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flat.update(_flatten(value, path))
    elif isinstance(obj, list):
        if not obj:
            flat[prefix or "."] = []
        for i, value in enumerate(obj):
            flat.update(_flatten(value, f"{prefix}[{i}]"))
    else:
        flat[prefix or "."] = obj
    return flat


def _json_keypath_diff(old: Any, new: Any) -> list[str]:
    """Semantic diff: key paths added/removed/changed, values masked."""
    old_flat, new_flat = _flatten(old), _flatten(new)
    lines: list[str] = []
    for path in sorted(old_flat.keys() | new_flat.keys()):
        in_old, in_new = path in old_flat, path in new_flat
        if in_old and in_new and old_flat[path] != new_flat[path]:
            lines.append(
                f"  ~ {path}: {display_value(path, old_flat[path])}"
                f" → {display_value(path, new_flat[path])}"
            )
        elif not in_old:
            lines.append(f"  + {path} = {display_value(path, new_flat[path])}")
        elif not in_new:
            lines.append(
                f"  - {path} (was {display_value(path, old_flat[path])})"
            )
    if not lines:
        lines.append("  (no key-path differences)")
    return lines


def _unified_diff(rel: str, old: bytes | None, new: bytes) -> list[str]:
    try:
        old_lines = (old or b"").decode("utf-8").splitlines()
        new_lines = new.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return ["  <binary file — diff withheld>"]
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{rel} (current)" if old is not None else "/dev/null",
        tofile=f"b/{rel} (profile)",
        lineterm="",
    )
    return [mask_line(line) for line in diff]


def render_file_plan(fp: FilePlan) -> str:
    """Masked, human-readable per-file plan block."""
    header = f"=== {fp.rel} ({fp.action})"
    if fp.action != "skip":
        header += f" -> {fp.target}"
    header += " ==="
    lines = [header]
    if fp.action == "skip":
        lines.append(f"  SKIP — {fp.skip_reason}")
        return "\n".join(lines)
    if fp.action == "unchanged":
        lines.append("  already matches — no write needed")
        return "\n".join(lines)
    if is_credential_file(fp.rel):
        lines.append("  <contents withheld — credential-carrying file>")
        return "\n".join(lines)

    old_obj = (
        try_load_json_bytes(fp.old_bytes) if fp.old_bytes is not None else None
    )
    new_obj = try_load_json_bytes(fp.new_bytes)
    if fp.old_bytes is not None and old_obj is not None and new_obj is not None:
        lines += _json_keypath_diff(old_obj, new_obj)
    else:
        lines += _unified_diff(fp.rel, fp.old_bytes, fp.new_bytes)
    return "\n".join(lines)


def render_plan(plans: Iterable[FilePlan]) -> str:
    return "\n".join(render_file_plan(fp) for fp in plans)


def profile_diff(
    a: Profile, b: Profile
) -> str:
    """Masked diff between two profiles, file by file."""
    blocks: list[str] = []
    for rel in sorted(a.files.keys() | b.files.keys()):
        in_a, in_b = rel in a.files, rel in b.files
        if in_a and not in_b:
            blocks.append(f"=== {rel} (only in {a.name}) ===")
            continue
        if in_b and not in_a:
            blocks.append(f"=== {rel} (only in {b.name}) ===")
            continue
        old, new = a.file_bytes(rel), b.file_bytes(rel)
        if old == new:
            blocks.append(f"=== {rel} (identical) ===")
            continue
        header = f"=== {rel} ({a.name} → {b.name}) ==="
        if is_credential_file(rel):
            blocks.append(
                header + "\n  <contents withheld — credential-carrying file>"
            )
            continue
        old_obj, new_obj = try_load_json_bytes(old), try_load_json_bytes(new)
        if old_obj is not None and new_obj is not None:
            blocks.append(
                header + "\n" + "\n".join(_json_keypath_diff(old_obj, new_obj))
            )
        else:
            diff = difflib.unified_diff(
                old.decode("utf-8", errors="replace").splitlines(),
                new.decode("utf-8", errors="replace").splitlines(),
                fromfile=f"a/{rel} ({a.name})",
                tofile=f"b/{rel} ({b.name})",
                lineterm="",
            )
            blocks.append(header + "\n" + "\n".join(mask_line(l) for l in diff))
    return "\n".join(blocks)


def summarize_json_top_keys(data: bytes, limit: int = 12) -> list[str]:
    """Top-level key paths of a JSON file — for ``show`` (never values)."""
    obj = try_load_json_bytes(data)
    if not isinstance(obj, dict):
        return []
    keys = sorted(str(k) for k in obj)
    shown = keys[:limit]
    if len(keys) > limit:
        shown.append(f"… +{len(keys) - limit} more")
    return shown
