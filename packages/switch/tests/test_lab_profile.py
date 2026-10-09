"""The bundled ``lab`` profile — the G3 A/B evaluation overlay.

These tests exercise the real ``profiles/lab/`` directory (not a
conftest-generated overlay) against the usual fake data/config roots.
"""

from __future__ import annotations

import json
from pathlib import Path

from devin_switch import cli, journal
from devin_switch.jsonc import load_jsonc
from devin_switch.profiles import get
from tests.conftest import tree_snapshot

REPO_PROFILES = Path(__file__).resolve().parents[1] / "profiles"


def lab_argv(roots, *args: str) -> list[str]:
    """CLI args on the fake data/config roots but the real repo
    ``profiles/`` dir — so the bundled ``lab`` overlay is exercised."""
    return [
        *args,
        "--data-dir",
        str(roots.data_dir),
        "--config-dir",
        str(roots.config_dir),
        "--profiles-dir",
        str(REPO_PROFILES),
    ]


def _whole_tree(roots) -> dict[str, bytes]:
    snap = tree_snapshot(roots.data_dir)
    snap.update(
        {
            f"config:{rel}": data
            for rel, data in tree_snapshot(roots.config_dir).items()
        }
    )
    return snap


def test_lab_discoverable_by_list(roots, capsys):
    assert cli.main(lab_argv(roots, "list")) == 0
    out = capsys.readouterr().out
    assert "lab" in out
    assert "corporate" in out
    assert "personal" in out


def test_lab_profile_semantics():
    """lab mirrors the same managed file set as the other profiles and
    carries the G3 invariants: pinned model, no hooks, no MCP servers."""
    profile = get(REPO_PROFILES, "lab")
    corporate = get(REPO_PROFILES, "corporate")
    assert set(profile.files) == set(corporate.files)

    config = load_jsonc(profile.files["config.json"])
    # no hook entries at all — an explicitly empty object
    assert config["hooks"] == {}
    # no implicit cross-attempt memory either
    assert config["cascade"]["autoGenerateMemories"] is False
    # one pinned model in every slot (placeholder documented in meta)
    models = config["models"]
    assert (
        models["defaultModel"]
        == models["secondaryModel"]
        == models["heavyModel"]
    )

    mcp = load_jsonc(profile.files["mcp_config.json"])
    assert mcp["mcpServers"] == {}

    meta = json.loads((profile.root / "profile.json").read_text())
    assert meta["model"] == models["defaultModel"]
    assert "devin_version_note" in meta


def test_show_lab(roots, capsys):
    assert cli.main(lab_argv(roots, "show", "lab")) == 0
    out = capsys.readouterr().out
    assert "profile: lab" in out
    assert "config.json" in out
    assert "mcp_config.json" in out
    assert "User/settings.json" in out


def test_diff_corporate_lab_shows_hooks_and_mcp_off(roots, capsys):
    assert cli.main(lab_argv(roots, "diff", "corporate", "lab")) == 0
    out = capsys.readouterr().out
    assert "diff corporate -> lab" in out
    # corporate's SessionStart audit hook disappears in lab
    assert "- hooks.SessionStart" in out
    assert "+ hooks = {}" in out
    # corporate's remote MCP gateway servers disappear in lab
    assert "- mcpServers.corp-gateway" in out
    assert "+ mcpServers = {}" in out


def test_use_lab_dry_run_writes_nothing(roots, capsys):
    before = _whole_tree(roots)
    assert cli.main(lab_argv(roots, "use", "lab")) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "--apply" in out
    assert _whole_tree(roots) == before
    assert not roots.ecosystem_dir.exists()


def test_use_lab_apply_then_rollback_restores_bytes(roots):
    before = _whole_tree(roots)

    assert cli.main(lab_argv(roots, "use", "lab", "--apply")) == 0
    lab_root = REPO_PROFILES / "lab"
    # the overlay landed verbatim (whole-file replace, comments kept)
    assert (roots.data_dir / "config.json").read_bytes() == (
        lab_root / "config.json"
    ).read_bytes()
    assert (roots.data_dir / "mcp_config.json").read_bytes() == (
        lab_root / "mcp_config.json"
    ).read_bytes()
    assert (
        roots.config_dir / "User" / "settings.json"
    ).read_bytes() == (lab_root / "User" / "settings.json").read_bytes()

    entry = journal.read_all(roots.journal_path)[-1]
    assert entry["action"] == "use"
    assert entry["profile"] == "lab"
    assert set(entry["files_changed"]) == {
        "config.json",
        "mcp_config.json",
        "User/settings.json",
    }

    assert cli.main(lab_argv(roots, "rollback", "--apply")) == 0
    residue = {
        rel: data
        for rel, data in _whole_tree(roots).items()
        if not rel.startswith("config:.devin-ecosystem/")
    }
    assert residue == before
