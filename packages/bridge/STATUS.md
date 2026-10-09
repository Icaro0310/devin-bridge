# STATUS

## Milestone M1 — done (2026-09-29)

- **Scaffold → Node.js.** Python template replaced by an ESM
  `package.json` (`bin: devin-bridge`, `node --test`, engines ≥20),
  Node CI matrix (Windows + Ubuntu × Node 22/24), reusable secrets-scan
  workflow kept. `.gitignore` covers `node_modules`, `.devin/` and
  root-local `.sessions.json`/`policy.json`.
- `src/policy.js` — permission policy engine (`policy.json` v1).
  Per-capability `allow`/`deny`/`ask` for terminal command lines, fs
  read/write paths and network hosts. Deny always wins; unmatched
  operations return the capability default — shipped default is `ask`
  (fail closed, never auto-approve). Path globs with `**`/zero-dir
  semantics for fs; wildcard mode for command lines and hosts; fs
  matching case-insensitive on win32. Built-in `fs.read` deny on
  credential stores (`credentials.toml`, `windsurf_api_key`) applies
  even under `allow: ["**"]`. `checkPermissionRequest` classifies ACP
  `toolCall.kind` (execute/read|search/edit|write|delete|move/fetch)
  into the right rule set.
- `src/acp-client.js` — clean port of the proven
  `gateways/src/devin-acp.js`: NDJSON JSON-RPC over stdio, initialize →
  authenticate (`_meta.api_key`, read fresh, never logged), session/new,
  session/load (`session_locked` surfaced via `AcpError.kind`),
  session/prompt with streamed text aggregation, modelLabel from
  `_cognition.ai/agent_stopped`, usage + recursive cost-field scan,
  client-side timeout → `session/cancel` + `timedOut:true` + partial
  text. Every agent→client capability (terminal/*, fs/*,
  request_permission) is gated through `Policy` + optional `askHandler`
  — the blind auto-approve of the original is gone.
- `src/dispatch.js` — `SessionMap` (.sessions.json: ids/cwd/timestamps
  only, atomic tmp+rename, tolerant of missing/corrupt file),
  `ensureSession` (explicit `--resume` > stored id > create; load
  failure → new + rewrite), `runTask` (ensure → persist → prompt).
- `bin/devin-bridge.js` — zero-dep CLI: `new`, `resume`, `prompt`
  (live stream to stderr, RESULT+TEXT on stdout), `sessions`,
  `policy --show|--init|--check`. TTY gets an interactive `[y/N]`
  askHandler; non-TTY is fail-closed unless `--yes`.
- `policy.example.json` shipped and drift-tested against
  `examplePolicyDoc()`.

## Done criteria check

- `node --test` — **55 tests, all green** on Windows / Node 24
  (policy: 28, acp-client: 17, dispatch: 10). No devin.exe needed —
  `tests/fixtures/fake-acp.mjs` is a scripted NDJSON agent over real
  stdio covering handshake, session lifecycle, permission/terminal/fs
  gating, cost extraction and timeout-cancel.
- `devin-bridge policy --show` works (built-in fail-closed policy);
  `--init` writes a documented `policy.json`; `--check` returns
  allow/deny/ask correctly.
- Not verified: live `new`/`prompt` against real `devin.exe` (requires
  consuming a real session; the dispatcher path is a faithful port of
  the validated `devin-repo-task.js`).

## Remaining for M2

- Slack adapter (reuse `gateways/src/slack*.js` patterns: mailbox or
  events → `runTask`).
- Webhook mode (HTTP in → dispatch → notify out).
- Cost reporting (aggregate `cost`/`usage` per repo from RESULT blocks).
- npm publish (`files` already whitelist bin/src/policy.example.json).
- Optional: `--policy` inside repo dir vs global; policy hot-reload;
  per-repo policy overrides via `<repo>/.devin-bridge.json`.

## Blockers

None.

## Notes / decisions

- **Node, not Python:** the proven ACP client is Node and `node --test`
  is stdlib — zero dependencies for the whole package. (KICKOFF-M1 was
  adjusted accordingly.)
- **Fail-closed over convenient:** the original auto-approved every
  permission; here `ask` is the default everywhere and headless asks
  resolve to deny. `--yes` is the explicit escape hatch.
- **Shell note:** the session shell is cmd.exe — no heredoc/`;`;
  git commits use multiple `-m` flags.
- Node 24 emits DEP0190 for `spawn(..., {shell:true})` with args —
  kept to match prior art (commands arrive policy-gated from the agent).
