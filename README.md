<div align="center">

<img src="assets/banner.svg" alt="devin-bridge" width="100%"/>

<a href="https://github.com/Icaro0310/devin-bridge/actions/workflows/tests.yml"><img src="https://github.com/Icaro0310/devin-bridge/actions/workflows/tests.yml/badge.svg" alt="tests"/></a>


</div>

# devin-bridge

> **Unofficial community project.** Not affiliated with, endorsed by, or
> sponsored by Cognition AI. "Devin" is a trademark of Cognition AI.

**[Português (BR)](README.pt-BR.md)** · English

A policy-gated bridge that drives `devin.exe acp` from the outside:
create/resume isolated Devin sessions per project, send prompts, stream
results — with a `policy.json` deciding what the session may do.

## The problem

Devin Desktop sessions are not scriptable. `devin -p` requires an
interactive `devin auth login`, `devin list` is a TUI, and the
community snippets that drive `devin.exe acp` directly **auto-approve
every permission request** — fine for a demo, dangerous to leave running
against a real repo overnight.

## Prior art

This tool speaks ACP over newline-delimited JSON-RPC, manages isolated Devin
sessions per project, and adds a permission gate for terminal, filesystem and
permission requests. See [docs/SPEC.md](docs/SPEC.md) for the protocol and
policy contract.

## What makes it Devin-native

- **Side-by-side:** generic ACP clients auto-approve or delegate to the
  agent's config; this one gates `terminal/*`, `fs/*` and
  `session/request_permission` through a per-repo `policy.json`
  (allow/deny/ask, deny-wins, fail-closed by default).
- **No-Devin:** pointless without it — transport is `devin.exe acp`,
  auth is the IDE's `windsurf_api_key` from `credentials.toml` (no PKCE
  login), sessions show up grouped by repo in Devin Desktop.
- **One sentence:** *drive Devin from the outside, with a seatbelt.*

## Install

Requires Node.js ≥ 20, Git, and an authenticated Devin CLI/Desktop install.

**Windows (PowerShell):**

```powershell
git clone https://github.com/Icaro0310/devin-bridge.git
cd devin-bridge
npm install -g .
```

**Linux:**

```bash
git clone https://github.com/Icaro0310/devin-bridge.git
cd devin-bridge
npm install -g .
```

The bridge reads `windsurf_api_key` from `%APPDATA%\\devin\\credentials.toml`
on Windows and `$XDG_DATA_HOME/devin/credentials.toml` on Linux (normally
`~/.local/share/devin/credentials.toml`). Override with `DEVIN_CREDENTIALS_PATH`;
the Devin CLI is resolved from `PATH` or `DEVIN_CLI_PATH`. The token is never
logged or persisted.

## Usage

The examples below use a policy file in the current directory. `new` and
`prompt` store a repo-to-session mapping in `.sessions.json`; keep that local
file out of commits because it contains session IDs and local paths.

**Windows (PowerShell):**

```powershell
devin-bridge policy --init
devin-bridge new "C:\src\my-repo"
devin-bridge prompt "C:\src\my-repo" "run the test suite and fix failures"
devin-bridge prompt "C:\src\my-repo" --file docs\KICKOFF.md
devin-bridge sessions
devin-bridge policy --check terminal "rm -rf /"
```

**Linux:**

```bash
devin-bridge policy --init
devin-bridge new "$HOME/src/my-repo"
devin-bridge prompt "$HOME/src/my-repo" "run the test suite and fix failures"
devin-bridge prompt "$HOME/src/my-repo" --file docs/KICKOFF.md
devin-bridge sessions
devin-bridge policy --check terminal "rm -rf /"
```

Policy `ask` decisions prompt the operator interactively on a TTY;
non-interactive runs stay fail-closed unless `--yes` is passed.

## Works with Devin alone (Devin-only mode)

devin-bridge *is* the Devin-only path: it drives `devin acp` directly using
the `credentials.toml` the Devin CLI already stores — no second runtime, no
message broker, no extra API key. Requirements are just Node.js >= 20 and a
signed-in Devin CLI (`devin` on PATH or `DEVIN_CLI_PATH`). The permission
policy is fail-closed by default: anything not explicitly allowed is denied,
and credentials are never logged or persisted.

## Limitations

- Uses the **undocumented** `acp` mode and `_meta.api_key` authentication
  of the Devin CLI; both may change without notice (tested against Devin CLI
  3000.10.x).
- Windows and Linux are supported. The executable and credentials file are
  resolved per OS; use `DEVIN_CLI_PATH` and `DEVIN_CREDENTIALS_PATH` to override.
- `session/load` cannot steal a session open elsewhere — it fails
  `session_locked` and the dispatcher falls back to `session/new`.
- Does not expose agent-side MCP servers (`mcpServers: []` is sent).

## Development

```bash
npm test        # node --test — stdlib runner, zero deps
```

Tests use a scripted fake ACP agent (`tests/fixtures/fake-acp.mjs`) over
real stdio — no Devin CLI binary or credentials are needed.

## License

MIT — see [LICENSE](LICENSE).


---

If this saved you debugging time, a ⭐ on the repo helps others find it.
