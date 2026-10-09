"""Profile discovery and loading.

A profile is a directory ``profiles/<name>/`` whose files map 1:1 onto the
managed Devin config space: ``User/settings.json`` lands under the UI
config dir, everything else under the data dir. An optional
``profile.json`` (not itself managed) carries ``description`` and
``notes``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

META_FILENAME = "profile.json"


class ProfileError(Exception):
    """Unknown or malformed profile."""


@dataclass
class Profile:
    name: str
    root: Path
    description: str = ""
    notes: list[str] = field(default_factory=list)
    # relative posix path -> absolute source file inside the profile dir
    files: dict[str, Path] = field(default_factory=dict)

    def file_bytes(self, rel: str) -> bytes:
        return self.files[rel].read_bytes()


def _read_meta(root: Path) -> tuple[str, list[str]]:
    meta = root / META_FILENAME
    if not meta.is_file():
        return "", []
    try:
        obj = json.loads(meta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return "", []
    if not isinstance(obj, dict):
        return "", []
    description = obj.get("description")
    notes = obj.get("notes")
    return (
        description if isinstance(description, str) else "",
        [str(n) for n in notes] if isinstance(notes, list) else [],
    )


def _is_managed_file(path: Path) -> bool:
    if path.name == META_FILENAME:
        return False
    return not (path.name.startswith(".") or "__pycache__" in path.parts)


def load_profile(root: Path) -> Profile:
    """Load one profile directory (``root`` = ``profiles/<name>``)."""
    name = root.name
    description, notes = _read_meta(root)
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not _is_managed_file(path):
            continue
        rel = PurePosixPath(path.relative_to(root)).as_posix()
        files[rel] = path
    return Profile(
        name=name, root=root, description=description, notes=notes, files=files
    )


def discover(profiles_dir: Path) -> dict[str, Profile]:
    """Every subdirectory of ``profiles_dir`` is a profile."""
    found: dict[str, Profile] = {}
    if not profiles_dir.is_dir():
        return found
    for child in sorted(profiles_dir.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            found[child.name] = load_profile(child)
    return found


def get(profiles_dir: Path, name: str) -> Profile:
    profiles = discover(profiles_dir)
    if name not in profiles:
        known = ", ".join(sorted(profiles)) or "(none)"
        raise ProfileError(
            f"unknown profile {name!r} — available: {known} "
            f"(in {profiles_dir})"
        )
    return profiles[name]
