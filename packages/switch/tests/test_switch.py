"""The write path through the CLI: dry-run, apply, journal, rollback."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from devin_switch import cli, journal

from tests.conftest import cli_argv, tree_snapshot


def _whole_tree(roots) -> dict[str, bytes]:
    snap = tree_snapshot(roots.data_dir)
    snap.update(
        {
            f"config:{rel}": data
            for rel, data in tree_snapshot(roots.config_dir).items()
        }
    )
    return snap


# ---------------------------------------------------------------------------
# dry-run
# ---------------------------------------------------------------------------


def test_use_dry_run_writes_nothing(roots, capsys):
    before = _whole_tree(roots)
    assert cli.main(cli_argv(roots, "use", "work")) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "--apply" in out
    # nothing changed, nothing created — not even .devin-ecosystem/
    assert _whole_tree(roots) == before
    assert not roots.ecosystem_dir.exists()


def test_rollback_dry_run_writes_nothing(roots, capsys):
    assert cli.main(cli_argv(roots, "use", "work", "--apply")) == 0
    capsys.readouterr()
    before = _whole_tree(roots)
    n_entries = len(journal.read_all(roots.journal_path))
    assert cli.main(cli_argv(roots, "rollback")) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert _whole_tree(roots) == before
    # a dry-run rollback does not even append to the journal
    assert len(journal.read_all(roots.journal_path)) == n_entries


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------


def test_use_apply_writes_profile_and_journal(roots):
    orig_config = (roots.data_dir / "config.json").read_bytes()
    orig_mcp = (roots.data_dir / "mcp_config.json").read_bytes()
    orig_settings = (
        roots.config_dir / "User" / "settings.json"
    ).read_bytes()

    assert cli.main(cli_argv(roots, "use", "work", "--apply")) == 0

    # managed files were written verbatim (whole-file replace)
    profile_root = roots.profiles_dir / "work"
    assert (roots.data_dir / "config.json").read_bytes() == (
        profile_root / "config.json"
    ).read_bytes()
    assert (roots.data_dir / "mcp_config.json").read_bytes() == (
        profile_root / "mcp_config.json"
    ).read_bytes()
    assert (roots.data_dir / "hooks.v1.json").is_file()
    assert (roots.config_dir / "User" / "settings.json").read_bytes() == (
        profile_root / "User" / "settings.json"
    ).read_bytes()

    # journal entry: action=use, files listed, backup dir recorded
    entries = journal.read_all(roots.journal_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["action"] == "use"
    assert entry["profile"] == "work"
    assert set(entry["files_changed"]) == {
        "config.json",
        "hooks.v1.json",
        "mcp_config.json",
        "User/settings.json",
    }
    backup_dir = Path(entry["backup_dir"])
    assert backup_dir.is_dir()

    # the snapshot holds the pre-switch bytes + a manifest with sha256
    assert (backup_dir / "config.json").read_bytes() == orig_config
    assert (backup_dir / "mcp_config.json").read_bytes() == orig_mcp
    assert (
        backup_dir / "User" / "settings.json"
    ).read_bytes() == orig_settings
    manifest = json.loads((backup_dir / "manifest.json").read_text())
    by_rel = {r["rel"]: r for r in manifest["files"]}
    assert by_rel["config.json"]["existed"] is True
    assert by_rel["config.json"]["sha256"] == hashlib.sha256(
        orig_config
    ).hexdigest()
    assert by_rel["hooks.v1.json"]["existed"] is False


def test_use_apply_is_atomic_no_tmp_left(roots):
    assert cli.main(cli_argv(roots, "use", "work", "--apply")) == 0
    leftovers = [
        p for p in roots.data_dir.rglob("*.devin-switch.tmp")
    ] + [p for p in roots.config_dir.rglob("*.devin-switch.tmp")]
    assert leftovers == []


def test_use_apply_second_time_is_noop(roots):
    assert cli.main(cli_argv(roots, "use", "work", "--apply")) == 0
    assert cli.main(cli_argv(roots, "use", "work", "--apply")) == 0
    entries = journal.read_all(roots.journal_path)
    assert [e["action"] for e in entries] == ["use", "use"]
    # second run changed nothing → no backup dir
    assert entries[1]["files_changed"] == []
    assert entries[1]["backup_dir"] is None


# ---------------------------------------------------------------------------
# rollback round-trip
# ---------------------------------------------------------------------------


def test_use_then_rollback_restores_exact_bytes(roots):
    before = _whole_tree(roots)
    assert cli.main(cli_argv(roots, "use", "work", "--apply")) == 0
    assert _whole_tree(roots) != before  # the switch really happened

    assert cli.main(cli_argv(roots, "rollback", "--apply")) == 0
    after = _whole_tree(roots)
    # every managed file restored byte-for-byte; created file removed;
    # the only residue is .devin-ecosystem bookkeeping itself
    residue = {
        rel: data
        for rel, data in after.items()
        if not rel.startswith("config:.devin-ecosystem/")
    }
    assert residue == before
    assert not (roots.data_dir / "hooks.v1.json").exists()

    entries = journal.read_all(roots.journal_path)
    assert [e["action"] for e in entries] == ["use", "rollback"]
    assert entries[1]["profile"] == "work"


def test_rollback_without_prior_use_fails_cleanly(roots, capsys):
    assert cli.main(cli_argv(roots, "rollback")) == 1
    assert cli.main(cli_argv(roots, "rollback", "--apply")) == 1
    assert "nothing to roll back" in capsys.readouterr().err
    assert not roots.ecosystem_dir.exists()


def test_rollback_restores_earlier_backup_not_latest_noop(roots):
    """After 'use work' then a no-op 'use work' (no backup), rollback must
    still find the real snapshot, not choke on the empty entry."""
    before = _whole_tree(roots)
    cli.main(cli_argv(roots, "use", "work", "--apply"))
    cli.main(cli_argv(roots, "use", "work", "--apply"))  # no-op entry
    assert cli.main(cli_argv(roots, "rollback", "--apply")) == 0
    after = _whole_tree(roots)
    for rel, data in before.items():
        assert after[rel] == data


# ---------------------------------------------------------------------------
# credentials.toml — never touched
# ---------------------------------------------------------------------------


def test_credentials_never_touched_even_if_profile_ships_one(
    roots, tmp_path
):
    evil = {
        "credentials.toml": '[auth]\ntoken = "hijacked"\n',
        "config.json": '{"models": {}}',
    }
    from tests.conftest import write_profile

    write_profile(roots.profiles_dir, "evil", evil)
    original = (roots.data_dir / "credentials.toml").read_bytes()

    assert cli.main(cli_argv(roots, "use", "evil", "--apply")) == 0
    assert (roots.data_dir / "credentials.toml").read_bytes() == original

    # and the journal records only the managed file — the skipped
    # credentials.toml never appears in files_changed
    entry = journal.read_all(roots.journal_path)[-1]
    assert entry["files_changed"] == ["config.json"]


def test_credentials_untouched_across_full_cycle(roots):
    digest = hashlib.sha256(
        (roots.data_dir / "credentials.toml").read_bytes()
    ).hexdigest()
    cli.main(cli_argv(roots, "use", "work", "--apply"))
    cli.main(cli_argv(roots, "use", "home", "--apply"))
    cli.main(cli_argv(roots, "rollback", "--apply"))
    cli.main(cli_argv(roots, "doctor"))
    assert (
        hashlib.sha256(
            (roots.data_dir / "credentials.toml").read_bytes()
        ).hexdigest()
        == digest
    )


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------


def test_use_unknown_profile_exits_1(roots, capsys):
    assert cli.main(cli_argv(roots, "use", "nope")) == 1
    assert "unknown profile" in capsys.readouterr().err
