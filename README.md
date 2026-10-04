<div align="center">

<img src="assets/banner.svg" alt="devin-orchestrator" width="100%"/>

<a href="https://github.com/Icaro0310/devin-orchestrator/actions/workflows/ci.yml"><img src="https://github.com/Icaro0310/devin-orchestrator/actions/workflows/ci.yml/badge.svg" alt="ci"/></a>


</div>

# devin-orchestrator

> Unofficial community project; not affiliated with or endorsed by Cognition AI.
>
> **[Português (BR)](README.pt-BR.md)** · English

Background-worker fan-out policy for Devin Desktop. It provides a skill/rule
and a deterministic planner; Devin executes the approved worker plan.

## What it is

Two layers:

1. **Skill + always-on rule** (`.devin/skills/devin-orchestrator/`,
   `.devin/rules/background-workers.md`) — model instructions: when a task
   has 2+ independent units or large scope, fan out instead of running
   serially in the main session.
2. **Deterministic planner** (`src/devin_orchestrator/planner.py`) — the
   hard limits live in code, not in prose. The model supplies structured
   signals about the task; the planner returns how many workers are allowed,
   which profile to use, and enforces caps that cannot be argued away.

## Policy (enforced in code)

| Signal | Plan |
|---|---|
| `kind=question` or `estimated_scope=trivial` | 0 workers — inline |
| `independent_units=1`, small/medium | 0 workers — inline |
| `independent_units=N` (N≥2) | min(N, 3) background workers |
| `kind=refactor` + large scope | up to 3 workers for disjoint slices |
| `DEVIN_INSIDE_SUBAGENT=1` | 0 workers — nesting forbidden |
| `needs_write=false` or `kind=review` | `subagent_explore` (read-only) |

Every fanned-out plan carries `collect=true`: the parent must gather worker
results before reporting. The plan is data only — no paths, no URLs, no
commands; the planner cannot create repos or touch the filesystem.


### `--explain` and file disjointness

```bash
devin-orchestrator plan '<spec>' --explain   # human-readable decision walkthrough
devin-orchestrator schema spec|plan          # print the published JSON Schemas
```

A spec may declare per-unit files so the planner can flag units that are
**not** disjoint before workers are launched:

```json
{"kind":"implementation","independent_units":2,"estimated_scope":"medium",
 "units_detail":[{"id":"api","files":["src/api/"]},
                 {"id":"ui","files":["src/ui/","src/api/x.py"]}]}
```

Collisions appear under `file_collisions` in the plan plus a warning — the
check is purely declarative (the planner never reads the filesystem). The
input spec and output plan are published as JSON Schemas
(`spec.schema.json`, `plan.schema.json`, also via `devin-orchestrator
schema`).

Note on packaging: the PyPI name `devin-orchestrator` belongs to another
author — this project ships as `devin-fanout` while the CLI stays
`devin-orchestrator`.

## Install

Python ≥ 3.10 and `pipx` are required. **Windows (PowerShell):** install `pipx` with `py -m pip install --user pipx`, run `py -m pipx ensurepath`, then reopen the terminal. **Linux (Debian/Ubuntu):** run `sudo apt install pipx python3-venv` and `pipx ensurepath`; reopen the terminal. Other Linux distributions should install `pipx` using their package manager.

Install the CLI from this repository:

```bash
pipx install "devin-orchestrator @ git+https://github.com/Icaro0310/devin-orchestrator.git"
```

## Usage

```bash
devin-orchestrator plan '{"kind":"implementation","independent_units":3,"needs_write":true,"estimated_scope":"large","summary":"API + UI + tests"}'
```

Output:

```json
{
  "workers": 3,
  "mode": "background",
  "profiles": ["subagent_general", "subagent_general", "subagent_general"],
  "collect": true,
  "warnings": [],
  "limits": {"max_workers": 3, "nesting": "forbidden"}
}
```

## Install in a workspace

Clone the repo so you can copy the Devin extension files:

```bash
git clone https://github.com/Icaro0310/devin-orchestrator.git
```

From the workspace root, copy the files using the shell for your OS.

**Windows (PowerShell):**

```powershell
New-Item -ItemType Directory -Force .devin\skills, .devin\rules | Out-Null
Copy-Item -Recurse devin-orchestrator\.devin\skills\devin-orchestrator .devin\skills\
Copy-Item devin-orchestrator\.devin\rules\background-workers.md .devin\rules\
```

**Linux:**

```bash
mkdir -p .devin/skills .devin/rules
cp -R devin-orchestrator/.devin/skills/devin-orchestrator .devin/skills/
cp devin-orchestrator/.devin/rules/background-workers.md .devin/rules/
```

The rule is always-on; the skill is model-triggered.


`record`/`history` (OR-3) keep a **local** log of plans vs. outcomes in
`plans.jsonl` — plan hash, worker count, mode, outcome, notes. It is a
registry, not telemetry: nothing leaves the machine.

## Limitations

The CLI only computes a JSON plan; it does not spawn workers or modify files.
The workspace skill/rule supplies the instructions, and actual worker execution
requires Devin's background-subagent support.

## CPU limits

- Absolute cap: **3 concurrent workers** (`DEVIN_MAX_WORKERS` can only lower).
- Heavy work (build/test) inside workers should run single-process.
- Prefer read-only workers for investigation.

## Development

```bash
pip install -e ".[dev]"
```

## Test

```bash
pytest -q   # behavioral matrix: trivial→0, units→min(N,3), nested→0, ...
```

## Works with Devin alone (Devin-only mode)

The planner runs locally; subagent execution happens inside Devin's own
runtime, so Devin is the only dependency — no separate agent framework, queue
or model server to install.

## Platform support

Workspace-level policy and thin wrappers — no platform-specific code.
Runs wherever Devin runs; CI tests on `windows-latest` + `ubuntu-latest`.

## When to use this

- Your Devin sessions run large multi-part tasks serially when they could
  fan out — the skill/rule teaches the model when parallelizing pays.
- You want worker limits enforced in code, not in prose: absolute cap of 3
  concurrent workers (`DEVIN_MAX_WORKERS` can only lower it), nesting
  forbidden under `DEVIN_INSIDE_SUBAGENT=1`.
- You want the right profile per task — read-only `subagent_explore` for
  investigation, `subagent_general` only when the task needs writes.
- You want every fanned-out plan to carry `collect=true`, so the parent
  must gather worker results before reporting.

## When NOT to use this

- You expect the CLI to spawn workers — it only computes a JSON plan; the
  workspace skill/rule supplies the instructions and Devin's runtime
  executes the workers.
- You are not working inside Devin — the whole policy presupposes Devin's
  background-subagent model.
- Your tasks are inherently serial or single-unit — the planner will just
  return 0 workers (correctly, but there is nothing to gain).

## FAQ

**What is devin-orchestrator?** A fan-out policy for Devin Desktop in two
parts: a `.devin/` skill + always-on rule that tells the model when to use
background workers, and a deterministic planner CLI that turns structured
task signals into an enforceable worker plan (how many, which profile,
`collect=true`).

**Does the planner create workers or touch files?** No. `devin-orchestrator
plan` outputs a JSON plan only — no paths, no URLs, no commands, no
filesystem access. Devin's own subagent runtime does the actual work.

**What are the hard limits?** At most 3 concurrent workers
(`DEVIN_MAX_WORKERS` can only lower it), 0 workers for trivial/question
tasks or single-unit jobs, 0 workers when already inside a subagent
(`DEVIN_INSIDE_SUBAGENT=1`), and read-only profiles for review or
no-write work.

**How do I install it in a workspace?** Copy `.devin/skills/devin-orchestrator/`
into your workspace's `.devin/skills/` and
`.devin/rules/background-workers.md` into `.devin/rules/` — the rule is
always-on and the skill is model-triggered. Copy commands for PowerShell
and Linux are in Usage above.

## License

MIT — see [LICENSE](LICENSE).
