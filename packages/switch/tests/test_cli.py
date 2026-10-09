"""Read-only subcommands: list / show / diff / doctor."""

from __future__ import annotations

import json

from devin_switch import cli

from tests.conftest import cli_argv, write_profile


def test_list_shows_profiles(roots, capsys):
    assert cli.main(cli_argv(roots, "list")) == 0
    out = capsys.readouterr().out
    assert "work" in out
    assert "home" in out
    assert "work overlay" in out


def test_list_empty_dir(roots, tmp_path, capsys):
    empty = tmp_path / "no-profiles"
    empty.mkdir()
    code = cli.main(
        [
            "list",
            "--data-dir",
            str(roots.data_dir),
            "--config-dir",
            str(roots.config_dir),
            "--profiles-dir",
            str(empty),
        ]
    )
    assert code == 0
    assert "no profiles" in capsys.readouterr().out


def test_show_prints_keys_not_values(roots, capsys):
    assert cli.main(cli_argv(roots, "show", "work")) == 0
    out = capsys.readouterr().out
    assert "config.json" in out
    assert "models" in out  # top-level key listed
    # show prints keys/targets only — nested values never leak
    assert "SWE-L15" not in out
    assert str(roots.data_dir / "mcp_config.json") in out


def test_show_unknown_profile(roots, capsys):
    assert cli.main(cli_argv(roots, "show", "nope")) == 1
    assert "unknown profile" in capsys.readouterr().err


def test_diff_between_profiles(roots, capsys):
    assert cli.main(cli_argv(roots, "diff", "work", "home")) == 0
    out = capsys.readouterr().out
    assert "config.json" in out
    assert "mcp_config.json" in out  # only in work
    assert "diff work -> home" in out
    # key-path diff markers
    assert "~" in out or "+" in out or "-" in out


def test_diff_unknown_profile(roots, capsys):
    assert cli.main(cli_argv(roots, "diff", "work", "nope")) == 1


def test_doctor_healthy(roots, capsys):
    assert cli.main(cli_argv(roots, "doctor")) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "closest profile" in out
    assert "credentials.toml" in out
    assert "never inspected" in out


def test_doctor_flags_broken_json(roots, capsys):
    (roots.data_dir / "config.json").write_text("{ not json", "utf-8")
    assert cli.main(cli_argv(roots, "doctor")) == 1
    assert "FAIL" in capsys.readouterr().out


def test_doctor_flags_bad_hook_shape(roots, capsys):
    bad = json.dumps(
        {"hooks": {"SessionStart": [{"hooks": [{"type": "bogus"}]}]}}
    )
    (roots.data_dir / "config.json").write_text(bad, "utf-8")
    assert cli.main(cli_argv(roots, "doctor")) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out


def test_doctor_warns_unknown_hook_event(roots, capsys):
    bad = json.dumps({"hooks": {"MadeUpEvent": []}})
    (roots.data_dir / "config.json").write_text(bad, "utf-8")
    assert cli.main(cli_argv(roots, "doctor")) == 0  # WARN, not FAIL
    assert "WARN" in capsys.readouterr().out


def test_credentials_in_profile_shows_withheld(roots, capsys):
    write_profile(
        roots.profiles_dir,
        "secretive",
        {
            "secrets.json": '{"api_key": "abc"}',
            "credentials.toml": '[auth]\ntoken = "x"\n',
        },
    )
    assert cli.main(cli_argv(roots, "show", "secretive")) == 0
    out = capsys.readouterr().out
    assert "<withheld" in out
    assert "abc" not in out
    assert "never managed" in out
