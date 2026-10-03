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

## License

MIT — see [LICENSE](LICENSE).
