# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- README gains the generated `Part of the DEVIN ecosystem` block
  (track/nature/audience/interface rendered from the registry).

- `labeler.yml` is now a thin caller of the shared reusable workflow in `devin-powerups` (`@v1`); PR labeling behavior is unchanged.

- README install section replaced by a generated `DIST-STATUS` banner stating the tool is source-only (no PyPI release yet) and offering both `pipx` and `uv` source installs.

### Added

- Read-only adapters: `devin_switch.mcp_server` MCP server
  (`switch_list_profiles`, `switch_preview_use`, `switch_diff`,
  `switch_doctor`, `devin-switch-mcp` entry point, `mcp` extra),
  Devin skill and `adapters/` plugin root. Profile descriptions pass
  through `mask_line` before reaching the MCP client, so a secret in
  `profile.json` free text is never exposed raw.

- `profiles/lab/` — G3 A/B evaluation overlay: pinned model
  (`SWE-2-High` — the free-tier model as of 2026-10-04),
  explicitly empty `hooks` and `mcpServers` (no learning-loop or
  prompt-logging hooks, no memory MCP, `autoGenerateMemories` off), and
  the serial-vs-isolated config-dir caveat documented in
  `profiles/README.md`. Mirrored in `src/devin_switch/profiles/` for
  pipx installs.

## [0.1.0] - 2026-10-04

### Added

- `devin-switch list` / `show <profile>` / `diff <a> <b>` — read-only
  profile inspection with values masked.
- `devin-switch use <profile>` — dry-run by default (masked per-file plan);
  `--apply` snapshots every file about to change into
  `.devin-ecosystem/switch-backups/<ts>/`, verifies sha256 of each copy
  against the manifest *and* the live source, then writes atomically
  (tmp + rename) and appends to `.devin-ecosystem/switch-journal.jsonl`.
- `devin-switch rollback` — dry-run by default; `--apply` restores the
  newest `use` backup (restores modified files, deletes created ones)
  and journals the rollback.
- `devin-switch doctor` — JSONC/hooks/MCP shape checks over both config
  roots (same documented shapes as devin-doctor, implemented inline) plus
  closest-profile ranking; exit 1 on any FAIL.
- `profiles/` example overlays: `corporate` (locked-down: remote MCP
  gateway, conservative cascade, audit hook) and `personal` (local stdio
  MCP servers, permissive cascade, session hooks), mirrored inside the
  package for pipx installs.
- Secret masking in all output: credential-named files withhold contents;
  sensitive key paths and token-looking values render as `<redacted>`.
- `credentials.toml` is never managed — not read, not written, ever.
- Test suite (62 tests) running entirely on synthetic tmp-dir roots —
  use→rollback round-trip, journal integrity, atomic-write leftovers,
  and end-to-end assertions that no literal secret reaches CLI output.
