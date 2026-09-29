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

This project adapts the proven client from
`personal-agent-system` (`gateways/src/devin-acp.js`, ~600 lines:
NDJSON JSON-RPC over stdio, session lifecycle, terminal/fs/permission
handlers, model/cost notifications) and its dispatcher
(`scripts/devin-repo-task.js`, repo→sessionId mapping). It does not
reinvent the protocol — it ports it and adds the missing permission
gate. See [docs/SPEC.md](docs/SPEC.md).

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

```bash
git clone https://github.com/Icaro0310/devin-bridge.git
cd devin-bridge
npm install -g .        # or: npm link
```

Requires Node ≥ 20 and a signed-in Devin Desktop (it reads the session
token from `%APPDATA%\devin\credentials.toml`; the token is never logged
or persisted).

## Usage

```bash
# optional: write a policy for the current project
devin-bridge policy --init          # creates ./policy.json (see policy.example.json)

# create an isolated session for a repo (recorded in .sessions.json)
devin-bridge new C:\path\to\repo

# dispatch a prompt — resumes the mapped session automatically
devin-bridge prompt C:\path\to\repo "run the test suite and fix failures"
devin-bridge prompt C:\path\to\repo --file docs\KICKOFF-M1.md --yes

# inspect
devin-bridge sessions
devin-bridge policy --check terminal "rm -rf /"
```

Policy `ask` decisions prompt the operator interactively on a TTY;
non-interactive runs stay fail-closed unless `--yes` is passed.

## Limitations

- Uses the **undocumented** `acp` mode and `_meta.api_key` auth of the
  bundled `devin.exe`; both may change without notice (authenticated
  against Devin CLI 3000.10.x).
- Windows-first (paths, spawn semantics); works on Linux CI for tests
  but real sessions target the Windows Desktop install.
- `session/load` cannot steal a session open elsewhere — it fails
  `session_locked` and the dispatcher falls back to `session/new`.
- Does not expose agent-side MCP servers (`mcpServers: []` is sent).

## Development

```bash
npm test        # node --test — stdlib runner, zero deps
```

Tests use a scripted fake ACP agent (`tests/fixtures/fake-acp.mjs`) over
real stdio — no `devin.exe` needed.

## License

MIT — see [LICENSE](LICENSE).
