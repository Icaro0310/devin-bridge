# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-29

### Added

- Node.js ESM package (`devin-bridge`, engines ≥20, zero runtime deps)
  replacing the initial Python scaffold.
- `src/acp-client.js` — ACP client for `devin.exe acp`: NDJSON JSON-RPC
  over stdio, `initialize`/`authenticate` (`_meta.api_key` =
  `windsurf_api_key`, never logged), `session/new`/`load`/`prompt`/
  `cancel`, `session/set_config_option`, streamed text + model label +
  usage/cost extraction, timeout-cancel semantics. Ported from
  `personal-agent-system/gateways/src/devin-acp.js`.
- `src/policy.js` — `policy.json` v1 permission engine: per-capability
  allow/deny/ask for terminal commands, fs read/write paths, network
  hosts; glob matching with deny-wins and fail-closed defaults;
  built-in deny on credential stores; `checkPermissionRequest`
  classifies ACP tool calls by `kind`.
- `src/dispatch.js` — `SessionMap` (atomic `.sessions.json`, ids only),
  `ensureSession` resume-or-create with fallback, `runTask` dispatch.
  Ported from `scripts/devin-repo-task.js`.
- `bin/devin-bridge.js` — CLI: `new`, `resume`, `prompt`, `sessions`,
  `policy --show|--init|--check`; interactive TTY askHandler, `--yes`
  escape hatch, `--sessions-file`/`--policy`/`--bin`/`--timeout-ms`.
- `policy.example.json` (sync-tested), bilingual READMEs, SPEC.md,
  STATUS.md.
- Test suite: 55 `node --test` cases with a scripted fake ACP agent
  fixture over real stdio — no `devin.exe` required.
- CI: Node matrix (Windows + Ubuntu × 22/24) + reusable secrets scan.

### Security

- Default policy is `ask` for every capability — headless runs fail
  closed instead of the original's blind auto-approve.
- `windsurf_api_key`/`credentials.toml` contents are never logged or
  persisted; `.sessions.json` holds ids/cwd/timestamps only.
