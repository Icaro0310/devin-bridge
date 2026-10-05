# devin-switch

> **Unofficial community project.** Not affiliated with, endorsed by, or
> sponsored by Cognition AI. "Devin" is a trademark of Cognition AI.

**[Windows](README.windows.md)** · **[Linux](README.linux.md)** · English

`devin-switch` swaps between named **Devin configuration profiles** —
hooks, MCP servers, models, cascade rules, UI settings — with a verified
snapshot before every write and a journal you can roll back from.
**Dry-run by default**: nothing is ever written unless you pass
`--apply`.

## The problem

Devin's behaviour lives in a handful of JSONC files spread across two
roots: `config.json` + `mcp_config.json` under the **data dir**
(`~/.config/devin`, `%APPDATA%/devin`) and `User/settings.json` under the
**UI config dir** (`~/.config/Devin`, `%APPDATA%/Devin`). Wanting a
locked-down "work" setup and a permissive "personal" setup means editing
the same files back and forth — by hand, with no undo.

`devin-switch` treats each variant as a declarative overlay directory and
does the swap safely.

## Safety model

- **Dry-run by default** — `use` and `rollback` print a masked plan and
  write *nothing* (not even the journal) without `--apply`.
- **Verified snapshot** — before any write, every file about to change is
  copied into `.devin-ecosystem/switch-backups/<ts>/` with a sha256
  manifest. The copies are re-hashed *and* compared against the live
  sources; any mismatch aborts before a single byte is written.
- **Atomic writes** — sibling tmp file + `os.replace`; no half-written
  config.
- **`credentials.toml` is never touched** — not read, not written, not
  even opened for a hash. A profile that ships one gets a `skip`.
- **Secrets masked in all output** — credential-named files
  (`.env*`, `*.pem`, `*secret*`, …) never have contents printed; inside
  printable files, values under sensitive key names (`token`, `secret`,
  `password`, `api_key`, `auth`…) or that look like tokens (long alnum
  blobs, JWTs, `sk-`/`ghp_`/`xox` prefixes) render as `<redacted>`.
- **No network** — stdlib only, Python ≥ 3.10.

## Install

Python ≥ 3.10 and `pipx` are required. **Windows (PowerShell):** install `pipx` with `py -m pip install --user pipx`, run `py -m pipx ensurepath`, then reopen the terminal. **Linux (Debian/Ubuntu):** run `sudo apt install pipx python3-venv` and `pipx ensurepath`; reopen the terminal.

```bash
pipx install "devin-switch @ git+https://github.com/Icaro0310/devin-switch.git"
```

(Not published on PyPI yet; the GitHub install above is the supported route.)

## Usage

```bash
devin-switch list                       # discovered profiles
devin-switch show personal              # what a profile manages (keys, not values)
devin-switch diff corporate personal    # masked diff between two profiles
devin-switch use personal               # DRY-RUN: masked per-file plan
devin-switch use personal --apply       # snapshot → verify → write → journal
devin-switch rollback                   # DRY-RUN: what would be restored
devin-switch rollback --apply           # restore the last verified backup
devin-switch doctor                     # config sanity + closest profile
```

Every command accepts `--data-dir`, `--config-dir` and `--profiles-dir`
to override the platform defaults (`--config-dir` falls back to
`--data-dir` for single-root layouts). The profiles dir resolves in
order: `--profiles-dir` → `$DEVIN_SWITCH_PROFILES_DIR` → `./profiles` →
the bundled examples.

Exit code is `0` on success/clean dry-run and `1` on errors — and for
`doctor`, on any `FAIL` check (like `devin-doctor`).

## Profiles

A profile is a directory under `profiles/` whose files map 1:1 onto the
managed config space — see [`profiles/README.md`](profiles/README.md):

```
profiles/
  corporate/
    profile.json          # metadata only — never copied
    config.json           # → <data-dir>/config.json
    mcp_config.json       # → <data-dir>/mcp_config.json
    User/settings.json    # → <config-dir>/User/settings.json
  personal/
    ...
```

Overlays are **whole-file replacements**, not merges — what the profile
ships is what the file becomes. Files are JSONC: `//` and `/* */`
comments allowed, trailing commas not.

### The `lab` profile (G3 A/B runs)

`profiles/lab/` is a hermetic config for A/B skill evaluation: a pinned
model — `SWE-2-High` (free tier as of 2026-10-04), the same id in
`config.json`, `User/settings.json` and `profile.json`, **no hooks
and no MCP servers at all** — deliberate, since learning-loop /
prompt-logging hooks and the memory MCP would let attempt n learn from
attempt n-1 — plus `autoGenerateMemories` off. Label sessions `g3-ab`.
Caveat: it is still unconfirmed whether Devin can isolate the config dir
per workspace; if it can't, run attempts **serially** and let
`devin-switch` swap `lab` in/out between them (`rollback` restores the
previous bytes exactly). See `profiles/README.md`.

## What happens on `--apply`

1. **Plan** — per file: `create` / `modify` / `unchanged` / `skip`
   (`credentials.toml`, unsafe paths).
2. **Snapshot** — pre-switch bytes copied to
   `~/.config/Devin/.devin-ecosystem/switch-backups/<timestamp>/` with a
   `manifest.json` recording sha256 per file (`existed: false` for files
   the switch would create).
3. **Verify** — every copy must hash to its recorded sha256 *and* still
   match the live source (catches a mid-switch edit). Any problem →
   abort, nothing written, backup kept as evidence.
4. **Write** — atomic tmp+rename per file.
5. **Journal** — one JSON line appended to
   `.devin-ecosystem/switch-journal.jsonl`:
   `{ts, action, profile, files_changed, backup_dir}`.

`rollback` reads the newest `use` entry whose backup still exists,
restores the snapshot (and deletes files the switch created), then
appends a `rollback` entry — the backup is *not* consumed, so you can
switch forward again afterwards.

## Development

```bash
python -m pytest            # 62 tests, all on synthetic tmp-dir fixtures
python -m devin_switch.cli doctor --profiles-dir profiles
```

The test suite runs entirely against fake Devin roots — no real
installation is touched, and `credentials.toml` fixtures are only ever
checked by digest.

## Related

- [`devin-doctor`](https://github.com/Icaro0310/devin-doctor) — diagnoses
  a Devin installation (read-only, always); `devin-switch doctor` covers
  the config-file corner of that space, inline, with no dependency.
