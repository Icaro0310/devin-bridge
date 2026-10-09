"""Secret masking — unit coverage plus the spec-required guarantee that
no literal secret ever reaches CLI output."""

from __future__ import annotations

import json

import pytest
from devin_switch import cli
from devin_switch.redact import (
    REDACTED,
    display_value,
    is_credential_file,
    is_never_touch,
    looks_secret,
    mask_line,
)

from tests.conftest import cli_argv, write_profile

SECRET = "sk-live-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"  # gitleaks-shaped
LONG_BLOB = "x9Kq2VbN7mPz4LwR8tYh3JfD6sAu1CgE5nBo0MiQ"
JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    "dozjgNryP4J3jVmNHl0w5N_XgL0n3I__P8w1g"
)


# ---------------------------------------------------------------------------
# unit-level heuristics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel,expected",
    [
        ("credentials.toml", True),
        ("User/credentials.toml", True),
        ("config.json", False),
        ("mcp_config.json", False),
        ("User/settings.json", False),
    ],
)
def test_is_never_touch(rel, expected):
    assert is_never_touch(rel) is expected


@pytest.mark.parametrize(
    "rel,expected",
    [
        (".env", True),
        (".env.production", True),
        ("secrets.json", True),
        ("my-credentials.json", True),
        ("server.pem", True),
        ("tls.key", True),
        ("config.json", False),
        ("User/settings.json", False),
    ],
)
def test_is_credential_file(rel, expected):
    assert is_credential_file(rel) is expected


@pytest.mark.parametrize(
    "value",
    [SECRET, LONG_BLOB, JWT, "ghp_abcdefghijklmnop1234567890"],
)
def test_looks_secret(value):
    assert looks_secret(value)


@pytest.mark.parametrize(
    "value", ["hello world", "SWE-16", "short", 42, True, None]
)
def test_looks_secret_rejects_normal(value):
    assert not looks_secret(value)


def test_display_value_masks_sensitive_key_paths():
    assert display_value("mcpServers.x.env.API_KEY", "abc") == REDACTED
    assert display_value("auth.token", "abc") == REDACTED
    assert display_value("models.defaultModel", "SWE-16") == '"SWE-16"'
    # 'author' must not trip the 'auth' heuristic
    assert display_value("meta.author", "ikaros") == '"ikaros"'


def test_display_value_masks_secret_looking_values():
    assert display_value("server.url", LONG_BLOB) == REDACTED


def test_mask_line_shapes():
    assert mask_line(f'+"API_KEY": "{SECRET}",') != f'+"API_KEY": "{SECRET}",'
    masked = mask_line(f'  "api_token": "{SECRET}"')
    assert SECRET not in masked
    assert REDACTED in masked
    masked = mask_line(f"TOKEN={LONG_BLOB}")
    assert LONG_BLOB not in masked
    masked = mask_line(f"Authorization: Bearer {JWT}")
    assert JWT not in masked
    # ordinary lines pass through
    line = '+  "defaultModel": "SWE-L15",'
    assert mask_line(line) == line


# ---------------------------------------------------------------------------
# end-to-end: no literal secret in any CLI output
# ---------------------------------------------------------------------------


def _secret_profile(roots):
    files = {
        "config.json": json.dumps(
            {
                "models": {"defaultModel": "SWE-16"},
                "remote": {"auth_token": SECRET, "refresh_token": JWT},
            },
            indent=2,
        ),
        "mcp_config.json": json.dumps(
            {
                "mcpServers": {
                    "hosted": {
                        "url": "https://mcp.example.com/x",
                        "env": {"API_KEY": LONG_BLOB},
                    }
                }
            },
            indent=2,
        ),
    }
    write_profile(roots.profiles_dir, "secretive", files)
    other = {
        "config.json": json.dumps({"models": {"defaultModel": "SWE-15"}}),
        "mcp_config.json": json.dumps({"mcpServers": {}}),
    }
    write_profile(roots.profiles_dir, "plain", other)


def test_no_literal_secret_in_use_dry_run(roots, capsys):
    _secret_profile(roots)
    assert cli.main(cli_argv(roots, "use", "secretive")) == 0
    out = capsys.readouterr().out
    for secret in (SECRET, LONG_BLOB, JWT):
        assert secret not in out
    assert REDACTED in out


def test_no_literal_secret_in_profile_diff(roots, capsys):
    _secret_profile(roots)
    assert cli.main(cli_argv(roots, "diff", "secretive", "plain")) == 0
    out = capsys.readouterr().out
    for secret in (SECRET, LONG_BLOB, JWT):
        assert secret not in out
    assert REDACTED in out


def test_no_literal_secret_in_show(roots, capsys):
    _secret_profile(roots)
    assert cli.main(cli_argv(roots, "show", "secretive")) == 0
    out = capsys.readouterr().out
    for secret in (SECRET, LONG_BLOB, JWT):
        assert secret not in out


def test_secrets_in_existing_config_masked_in_diff(roots, capsys):
    """Secrets already sitting in the live config must also be masked."""
    _secret_profile(roots)
    live = json.dumps(
        {
            "models": {"defaultModel": "SWE-16"},
            "remote": {"auth_token": SECRET},
        },
        indent=2,
    )
    (roots.data_dir / "config.json").write_text(live, "utf-8")
    assert cli.main(cli_argv(roots, "use", "plain")) == 0
    out = capsys.readouterr().out
    assert SECRET not in out
