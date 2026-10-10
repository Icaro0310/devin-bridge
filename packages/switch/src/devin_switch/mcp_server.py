"""devin-switch as an MCP server: the read-only surface exposed as tools.

Four tools — ``switch_status``, ``switch_list_profiles``, ``switch_diff``
and ``switch_preview`` — return the same data the CLI's read subcommands
print (``doctor``, ``list``, ``diff``, and the dry-run half of ``use``).
``switch_preview`` is the dry-run plan only: it reads the profile and the
live targets, computes actions, and writes nothing — exactly like the
CLI's dry-run, which never creates bookkeeping dirs either.

Read-only by construction: only ``profiles``, ``plan`` and ``health``
are imported. The write path stays exclusively in the CLI where a human
confirms it — nothing here can modify the user's config.

The logic lives in ``do_*`` functions, unit-testable without a running
server or the ``mcp`` package. ``build_server()`` wraps them — needs the
``mcp`` extra: ``pip install 'devin-switch[mcp]'``.
"""

from __future__ import annotations

from pathlib import Path

from devin_switch import paths as paths_mod
from devin_switch.health import check_config_files, rank_profiles
from devin_switch.paths import Roots
from devin_switch.plan import build_plan, profile_diff, render_plan
from devin_switch.profiles import ProfileError, discover, get


def _roots(data_dir: str, config_dir: str, profiles_dir: str) -> Roots:
    """Resolve the three roots exactly like the CLI's ``_roots``."""
    data = (
        Path(data_dir).expanduser()
        if data_dir
        else paths_mod.default_data_dir()
    )
    if config_dir:
        config = Path(config_dir).expanduser()
    elif data_dir:
        # single-root mode: one dir holds both data files and User/
        config = data
    else:
        config = paths_mod.default_config_dir()
    return Roots(
        data_dir=data,
        config_dir=config,
        profiles_dir=paths_mod.resolve_profiles_dir(
            Path(profiles_dir).expanduser() if profiles_dir else None
        ),
    )


def do_status(
    data_dir: str = "", config_dir: str = "", profiles_dir: str = ""
) -> dict:
    """The ``devin-switch doctor`` payload as a dict: per-file checks
    (PASS/WARN/FAIL) plus every profile ranked by distance — distance 0
    is the profile that exactly matches the live config."""
    roots = _roots(data_dir, config_dir, profiles_dir)
    checks = check_config_files(roots)
    found = discover(roots.profiles_dir)
    ranked = rank_profiles(found, roots) if found else []
    closest = None
    if ranked:
        best, dist = ranked[0]
        noun = "file" if dist == 1 else "files"
        closest = {
            "name": best.name,
            "distance": dist,
            "state": "exactly matches" if dist == 0 else f"{dist} {noun} away",
        }
    return {
        "ok": not any(r.status == "FAIL" for r in checks),
        "checks": [
            {"status": r.status, "label": r.label, "detail": r.detail}
            for r in checks
        ],
        "closest": closest,
        "profiles": [
            {"name": profile.name, "distance": d} for profile, d in ranked
        ],
        "roots": {
            "data_dir": str(roots.data_dir),
            "config_dir": str(roots.config_dir),
            "profiles_dir": str(roots.profiles_dir),
        },
    }


def do_list_profiles(
    data_dir: str = "", config_dir: str = "", profiles_dir: str = ""
) -> dict:
    """The ``devin-switch list`` payload: every discovered profile with
    its managed-file count and description."""
    roots = _roots(data_dir, config_dir, profiles_dir)
    found = discover(roots.profiles_dir)
    return {
        "profiles_dir": str(roots.profiles_dir),
        "profiles": [
            {
                "name": p.name,
                "files": len(p.files),
                "description": p.description,
            }
            for p in found.values()
        ],
    }


def do_diff(
    a: str,
    b: str,
    data_dir: str = "",
    config_dir: str = "",
    profiles_dir: str = "",
) -> dict:
    """The ``devin-switch diff <a> <b>`` payload: a masked per-file diff
    between two profiles. Unknown profile → ``{"error": ...}``."""
    roots = _roots(data_dir, config_dir, profiles_dir)
    try:
        profile_a = get(roots.profiles_dir, a)
        profile_b = get(roots.profiles_dir, b)
    except ProfileError as exc:
        return {"error": "ProfileError", "detail": str(exc)}
    return {
        "a": a,
        "b": b,
        "masked": True,
        "diff": profile_diff(profile_a, profile_b),
    }


def do_preview(
    profile: str,
    data_dir: str = "",
    config_dir: str = "",
    profiles_dir: str = "",
) -> dict:
    """The dry-run plan for ``use <profile>`` — per-file action
    (create/modify/unchanged/skip) plus the masked rendered plan.
    Writes nothing; unknown profile → ``{"error": ...}``."""
    roots = _roots(data_dir, config_dir, profiles_dir)
    try:
        prof = get(roots.profiles_dir, profile)
    except ProfileError as exc:
        return {"error": "ProfileError", "detail": str(exc)}
    plans = build_plan(prof, roots)
    counts: dict[str, int] = {}
    for fp in plans:
        counts[fp.action] = counts.get(fp.action, 0) + 1
    return {
        "profile": profile,
        "dry_run": True,
        "actions": counts,
        "files": [
            {
                "rel": fp.rel,
                "target": str(fp.target),
                "action": fp.action,
                "skip_reason": fp.skip_reason,
            }
            for fp in plans
        ],
        "plan": render_plan(plans),
    }


def _err(error: Exception) -> dict:
    return {"error": type(error).__name__, "detail": str(error)[:500]}


def _make_app(name: str):
    """Return an MCP server app across SDK versions.

    mcp 2.x renamed FastMCP -> MCPServer; both expose the same .tool()
    decorator and .run(transport='stdio'). Support whichever is installed.
    """
    try:  # mcp 2.x
        from mcp.server.mcpserver import MCPServer
        return MCPServer(name)
    except ImportError:
        pass
    try:  # mcp 1.x
        from mcp.server.fastmcp import FastMCP
        return FastMCP(name)
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "The MCP server needs the 'mcp' extra: "
            "pip install 'devin-switch[mcp]'"
        ) from e


def build_server():
    """Build the MCP server app with every devin-switch tool registered."""
    server = _make_app("devin-switch")

    @server.tool()
    def switch_status(
        data_dir: str = "", config_dir: str = "", profiles_dir: str = ""
    ) -> dict:
        """Health-check the Devin config like ``devin-switch doctor``:
        per-file PASS/WARN/FAIL checks plus profiles ranked by distance
        (distance 0 = the profile currently in effect). Read-only.
        ``ok`` is false when any check FAILs; ``error`` means it could
        not run at all.
        """
        try:
            return do_status(
                data_dir=data_dir,
                config_dir=config_dir,
                profiles_dir=profiles_dir,
            )
        except Exception as error:  # noqa: BLE001 — tool boundary must not raise
            return _err(error)

    @server.tool()
    def switch_list_profiles(
        data_dir: str = "", config_dir: str = "", profiles_dir: str = ""
    ) -> dict:
        """List the profiles ``devin-switch list`` would show: name,
        managed-file count and description for each profile discovered
        under ``profiles_dir`` (or the default location). Read-only.
        """
        try:
            return do_list_profiles(
                data_dir=data_dir,
                config_dir=config_dir,
                profiles_dir=profiles_dir,
            )
        except Exception as error:  # noqa: BLE001 — tool boundary must not raise
            return _err(error)

    @server.tool()
    def switch_diff(
        a: str,
        b: str,
        data_dir: str = "",
        config_dir: str = "",
        profiles_dir: str = "",
    ) -> dict:
        """Masked per-file diff between two profiles, like
        ``devin-switch diff <a> <b>`` — values are redacted and
        credential-carrying files are withheld. Read-only. ``error`` in
        the payload means an unknown profile name.
        """
        try:
            return do_diff(
                a=a,
                b=b,
                data_dir=data_dir,
                config_dir=config_dir,
                profiles_dir=profiles_dir,
            )
        except Exception as error:  # noqa: BLE001 — tool boundary must not raise
            return _err(error)

    @server.tool()
    def switch_preview(
        profile: str,
        data_dir: str = "",
        config_dir: str = "",
        profiles_dir: str = "",
    ) -> dict:
        """Preview what switching to ``profile`` would change — the same
        plan the CLI's dry-run prints: per-file action
        (create/modify/unchanged/skip), action counts and the masked
        rendered plan in ``plan``. Read-only: computes the plan and
        writes nothing. ``error`` means an unknown profile.
        """
        try:
            return do_preview(
                profile=profile,
                data_dir=data_dir,
                config_dir=config_dir,
                profiles_dir=profiles_dir,
            )
        except Exception as error:  # noqa: BLE001 — tool boundary must not raise
            return _err(error)

    return server


def main() -> None:
    build_server().run(transport="stdio")


if __name__ == "__main__":
    main()
