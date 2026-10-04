# profiles/

Example Devin configuration profiles for `devin-switch`.

## The overlay model

A profile is a directory whose files map **1:1 onto the managed Devin
config space**. `devin-switch use <name>` copies each file **verbatim**
(whole-file replace, not a merge) to its target:

| profile-relative path      | target                                        |
| -------------------------- | --------------------------------------------- |
| `User/settings.json`       | `<config-dir>/User/settings.json`             |
| `config.json`              | `<data-dir>/config.json`                      |
| `mcp_config.json`          | `<data-dir>/mcp_config.json`                  |
| anything else              | `<data-dir>/<path>`                           |

- **data dir** — `~/.config/devin` (Linux), `%APPDATA%/devin` (Windows)
- **config dir** — `~/.config/Devin` (Linux), `%APPDATA%/Devin` (Windows)

An optional `profile.json` inside the profile dir carries `description`
and `notes`; it is never copied.

Files are JSONC — `//` and `/* */` comments are allowed, trailing commas
are not.

## Never managed

`credentials.toml` is **never** read or written. A profile that contains
one gets a `skip` in the plan — the file is simply not managed. Other
credential-named files (`.env*`, `*.pem`, `*secret*`, …) may be applied
but their contents are withheld from every diff and `show` output.

## The two examples

- `corporate/` — locked-down: cascade auto-execution and web requests
  disabled, `terminal.execute` requires approval, MCP goes through a
  remote gateway (no local server processes), audit hooks on
  `SessionStart`.
- `personal/` — permissive: local stdio MCP servers (memory, filesystem,
  obsidian), ACP enabled, a prompt hook plus session start/end hooks.

Edit a copy in `./profiles` (or point `--profiles-dir` /
`DEVIN_SWITCH_PROFILES_DIR` at your own directory) — these are starting
points, not prescriptions.
