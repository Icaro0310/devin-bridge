"""``devin-switch doctor`` — closest profile + config sanity checks.

The hooks/MCP shape checks mirror the documented shapes (the same ones
devin-doctor validates: ``{event: [{matcher?, hooks: [{type, command|
prompt}]}]}`` and ``{"mcpServers": {name: {command|url}}}``) but are
implemented inline — devin-switch is stdlib-only and deliberately does NOT
depend on the devin-doctor package.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from devin_switch.jsonc import load_jsonc
from devin_switch.paths import Roots
from devin_switch.plan import build_plan
from devin_switch.profiles import Profile

KNOWN_HOOK_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "UserPromptSubmit",
    "Stop",
    "PostCompaction",
    "SessionStart",
    "SessionEnd",
}

_CONFIG_FILES = ("config.json", "mcp_config.json", "hooks.v1.json")


@dataclass
class CheckResult:
    status: str  # PASS | WARN | FAIL
    label: str
    detail: str


# ---------------------------------------------------------------------------
# shape validation (documented hooks/MCP shapes, inline)
# ---------------------------------------------------------------------------


def hooks_problems(obj: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(obj, dict):
        return ["hooks object must be a JSON object"], []
    for event, groups in obj.items():
        if event not in KNOWN_HOOK_EVENTS:
            warnings.append(f"unknown hook event '{event}'")
        if not isinstance(groups, list):
            errors.append(f"'{event}' must be a list of hook groups")
            continue
        for gi, group in enumerate(groups):
            if not isinstance(group, dict) or not isinstance(
                group.get("hooks"), list
            ):
                errors.append(
                    f"'{event}' group {gi} must be an object with a "
                    "'hooks' list"
                )
                continue
            for hi, hook in enumerate(group["hooks"]):
                if not isinstance(hook, dict):
                    errors.append(
                        f"'{event}' group {gi} hook {hi} not an object"
                    )
                    continue
                htype = hook.get("type")
                if htype == "command" and not isinstance(
                    hook.get("command"), str
                ):
                    errors.append(
                        f"'{event}' group {gi} hook {hi}: 'command' hooks "
                        "need a 'command' string"
                    )
                elif htype == "prompt" and not isinstance(
                    hook.get("prompt"), str
                ):
                    errors.append(
                        f"'{event}' group {gi} hook {hi}: 'prompt' hooks "
                        "need a 'prompt' string"
                    )
                elif htype not in ("command", "prompt"):
                    errors.append(
                        f"'{event}' group {gi} hook {hi}: type must be "
                        "'command' or 'prompt'"
                    )
    return errors, warnings


def mcp_problems(obj: Any) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    if not isinstance(obj, dict):
        return ["mcp config must be a JSON object"], []
    servers = obj.get("mcpServers")
    if servers is None:
        warnings.append("no 'mcpServers' key")
        return [], warnings
    if not isinstance(servers, dict):
        return ["'mcpServers' must be an object"], warnings
    for name, server in servers.items():
        if not isinstance(server, dict) or not (
            isinstance(server.get("command"), str)
            or isinstance(server.get("url"), str)
        ):
            warnings.append(
                f"server '{name}' has neither a 'command' nor a 'url'"
            )
    return [], warnings


def config_problems(obj: Any) -> tuple[list[str], list[str]]:
    if not isinstance(obj, dict):
        return ["config file must be a JSON object"], []
    errors: list[str] = []
    warnings: list[str] = []
    if "hooks" in obj:
        e, w = hooks_problems(obj["hooks"])
        errors += e
        warnings += w
    if "mcpServers" in obj:
        warnings.append(
            "'mcpServers' in config.json is the legacy location — Devin "
            "migrates it to mcp_config.json automatically"
        )
    return errors, warnings


def _validator_for(filename: str):
    if filename == "hooks.v1.json":
        return hooks_problems
    if filename.startswith("mcp_config"):
        return mcp_problems
    return config_problems


def check_config_files(roots: Roots) -> list[CheckResult]:
    """Parse + shape-check the managed config files under BOTH roots.

    ``credentials.toml`` is reported by presence only — never opened.
    """
    results: list[CheckResult] = []
    roots_seen = {roots.data_dir, roots.config_dir}
    any_file = False
    for root in sorted(roots_seen):
        for name in _CONFIG_FILES:
            path = root / name
            if not path.is_file():
                continue
            any_file = True
            label = f"{root.name}/{name}"
            try:
                obj = load_jsonc(path)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
                results.append(
                    CheckResult("FAIL", label, f"invalid JSON — {exc}")
                )
                continue
            errors, warnings = _validator_for(name)(obj)
            if errors:
                results.append(
                    CheckResult("FAIL", label, errors[0])
                )
            elif warnings:
                results.append(
                    CheckResult("WARN", label, warnings[0])
                )
            else:
                results.append(CheckResult("PASS", label, "OK"))
    settings = roots.config_dir / "User" / "settings.json"
    if settings.is_file():
        any_file = True
        try:
            obj = load_jsonc(settings)
            status = "PASS" if isinstance(obj, dict) else "WARN"
            detail = (
                "OK" if isinstance(obj, dict) else "settings.json is not "
                "a JSON object"
            )
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            status, detail = "FAIL", f"invalid JSON — {exc}"
        results.append(CheckResult(status, "User/settings.json", detail))
    if not any_file:
        results.append(
            CheckResult("WARN", "config files", "no managed config files "
                        "found under either root")
        )
    cred = _find_credentials(roots)
    results.append(
        CheckResult(
            "PASS" if cred is not None else "WARN",
            "credentials.toml",
            f"present (never inspected — by design): {cred}"
            if cred is not None
            else "absent",
        )
    )
    return results


def _find_credentials(roots: Roots) -> Path | None:
    """First existing ``credentials.toml`` across the plausible roots —
    checked by ``is_file()`` only, the file is never opened.

    Linux installs split them: ``~/.local/share/devin`` holds
    ``credentials.toml`` + stores while ``~/.config/devin`` holds the
    JSONC config — so the data dir alone is not enough.
    """
    env = os.environ
    candidates = [
        roots.data_dir,
        roots.config_dir,
        Path(env.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        / "devin",
        Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        / "devin",
        Path.home() / "devin",
    ]
    seen: set[Path] = set()
    for root in candidates:
        if root in seen:
            continue
        seen.add(root)
        path = root / "credentials.toml"
        if path.is_file():
            return path
    return None


# ---------------------------------------------------------------------------
# closest profile
# ---------------------------------------------------------------------------


def profile_distance(profile: Profile, roots: Roots) -> int:
    """Number of managed files that differ or are missing/extra relative
    to the profile (skipped files excluded)."""
    return sum(1 for fp in build_plan(profile, roots) if fp.needs_write)


def rank_profiles(profiles: dict[str, Profile], roots: Roots):
    """[(profile, distance)] sorted ascending."""
    ranked = [
        (profile, profile_distance(profile, roots))
        for profile in profiles.values()
    ]
    ranked.sort(key=lambda item: (item[1], item[0].name))
    return ranked
