# KICKOFF M1 — devin-bridge

Dedicated session for THIS repo — RESEARCH wave; the ACP client already
exists in the orchestrator workspace (this repo ports + hardens it).
`docs/SPEC.md` EN, a shared README plus Windows/Linux platform guides, logic in `src/devin_bridge/` + thin
`cli.py`, small commits + Devin trailer, push, STATUS.md + CHANGELOG.md.

## One sentence

A policy-gated bridge that drives `devin.exe acp` from the outside —
create/resume isolated sessions per project, send prompts, stream
results — with a permission policy file deciding what the session may do.

## Prior art / base material

The proven client is
`feat/personal-agent-system/gateways/src/devin-acp.js` (Node.js, ~600
lines: JSON-RPC over stdio, session/new|load|prompt|cancel, terminal+fs+permission
handlers, model/cost notifications) and
`scripts/devin-repo-task.js` (dispatcher + .sessions.json mapping).

**M1 = port the CORE to a clean, documented `devin-bridge` Node package**
(NOT Python — keep Node because ACP client is Node). Adjust the template:
`src/` JS ESM modules, `package.json` bin `devin-bridge`, tests with
`node --test`. Rewrite pyproject → package.json accordingly.

## Scope (M1)

`src/`:
- `acp-client.js` — clean port of devin-acp.js core (init handshake,
  session lifecycle, stdio JSON-RPC, notification surfacing).
- `policy.js` — `policy.json`: per-tool allow/deny/ask
  (terminal patterns, fs paths, network) — replaces blind auto-approve.
- `dispatch.js` — repo→session mapping file, resume logic (port of
  devin-repo-task.js behavior).
- `bin/devin-bridge.js` — CLI: `new|resume|prompt|sessions|policy`.

## Tests

`node --test tests/` — protocol framing unit tests (fake stdin/stdout
child), policy matching (glob patterns, deny-wins), session mapping
persistence. Mock the ACP binary — no real devin.exe in tests.

## Security requirements (hard)

- Default policy = ASK for terminal/fs (fail closed), not auto-approve.
- Never log `windsurf_api_key` or credentials.toml contents.
- `.sessions.json` contains ids only, no secrets.

## Env notes

Node v24; `node --test` is stdlib — no deps needed. Windows paths.

## Done

Tests green · `devin-bridge policy --show` works · docs real · pushed.
M2 queue in STATUS.md: Slack adapter, webhook mode, cost reporting,
npm publish.
