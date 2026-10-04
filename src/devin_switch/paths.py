"""Locations of Devin's config stores and the ecosystem bookkeeping dir.

Two roots matter for profile switching:

- the *data* dir — ``%APPDATA%/devin`` on Windows,
  ``$XDG_CONFIG_HOME/devin`` (normally ``~/.config/devin``) on Linux,
  ``~/Library/Application Support/devin`` on macOS. Holds ``config.json``
  (hooks, models, cascade rules), ``mcp_config.json`` and
  ``credentials.toml``.
- the UI *config* dir — ``%APPDATA%/Devin``, ``~/.config/Devin``,
  ``~/Library/Application Support/Devin``. Holds ``User/settings.json``
  and other UI stores.

A profile file whose relative path starts with ``User/`` targets the config
dir; any other relative path targets the data dir — matching Devin's real
on-disk split on both Windows and Linux.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ECOSYSTEM_DIRNAME = ".devin-ecosystem"
BACKUPS_DIRNAME = "switch-backups"
JOURNAL_FILENAME = "switch-journal.jsonl"


def default_data_dir(
    environ: dict[str, str] | None = None, platform: str | None = None
) -> Path:
    env = os.environ if environ is None else environ
    plat = sys.platform if platform is None else platform
    override = env.get("DEVIN_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if plat.startswith("win"):
        appdata = env.get("APPDATA")
        if appdata:
            return Path(appdata) / "devin"
        return Path.home() / "AppData" / "Roaming" / "devin"
    if plat == "darwin":
        return Path.home() / "Library" / "Application Support" / "devin"
    config_home = Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    data_home = Path(
        env.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    )
    candidates = [config_home / "devin", data_home / "devin", Path.home() / "devin"]
    # Prefer a root that actually holds config files; fall back to the
    # conventional XDG_CONFIG_HOME location.
    return next(
        (
            root
            for root in candidates
            if (root / "config.json").is_file()
            or (root / "mcp_config.json").is_file()
        ),
        candidates[0],
    )


def default_config_dir(
    environ: dict[str, str] | None = None, platform: str | None = None
) -> Path:
    env = os.environ if environ is None else environ
    plat = sys.platform if platform is None else platform
    override = env.get("DEVIN_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    if plat.startswith("win"):
        appdata = env.get("APPDATA")
        if appdata:
            return Path(appdata) / "Devin"
        return Path.home() / "AppData" / "Roaming" / "Devin"
    if plat == "darwin":
        return Path.home() / "Library" / "Application Support" / "Devin"
    config_home = Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    candidates = [config_home / "Devin", config_home / "devin"]
    return next(
        (root for root in candidates if (root / "User").is_dir()),
        candidates[0],
    )


@dataclass(frozen=True)
class Roots:
    """The three directories a command operates on."""

    data_dir: Path
    config_dir: Path
    profiles_dir: Path

    @property
    def ecosystem_dir(self) -> Path:
        """Bookkeeping lives under the UI config dir — the stable root."""
        return self.config_dir / ECOSYSTEM_DIRNAME

    @property
    def backups_dir(self) -> Path:
        return self.ecosystem_dir / BACKUPS_DIRNAME

    @property
    def journal_path(self) -> Path:
        return self.ecosystem_dir / JOURNAL_FILENAME


def bundled_profiles_dir() -> Path:
    """Example profiles shipped inside the package."""
    return Path(__file__).resolve().parent / "profiles"


def resolve_profiles_dir(
    arg: Path | None, environ: dict[str, str] | None = None
) -> Path:
    """``--profiles-dir`` > ``DEVIN_SWITCH_PROFILES_DIR`` > ``./profiles``
    (repo checkout / cwd) > bundled examples inside the package."""
    env = os.environ if environ is None else environ
    if arg is not None:
        return arg.expanduser()
    override = env.get("DEVIN_SWITCH_PROFILES_DIR")
    if override:
        return Path(override).expanduser()
    cwd_profiles = Path.cwd() / "profiles"
    if (cwd_profiles / "corporate").is_dir() or (cwd_profiles / "personal").is_dir():
        return cwd_profiles
    return bundled_profiles_dir()


def target_for(rel: str, roots: Roots) -> Path:
    """Map a profile-relative path to its absolute target.

    ``User/...`` → under the config dir; everything else → under the data
    dir. Refuses to escape the roots (``..`` segments, absolute paths).
    """
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe profile path: {rel!r}")
    parts = pure.parts
    if not parts:
        raise ValueError(f"empty profile path: {rel!r}")
    if parts[0] == "User":
        return roots.config_dir.joinpath(*parts)
    return roots.data_dir.joinpath(*parts)
