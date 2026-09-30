# devin-orchestrator

Background-worker fan-out policy for Devin Desktop. Decompose non-trivial
work into disjoint units, run them as background subagents, and keep the
main session interactive — the user can keep typing while workers run.

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

## Usage

```bash
pip install -e ".[dev]"
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

Copy `.devin/skills/devin-orchestrator/` into your workspace's `.devin/skills/`
and `.devin/rules/background-workers.md` into `.devin/rules/`. The rule is
always-on; the skill is model-triggered.

## CPU limits

- Absolute cap: **3 concurrent workers** (`DEVIN_MAX_WORKERS` can only lower).
- Heavy work (build/test) inside workers should run single-process.
- Prefer read-only workers for investigation.

## Test

```bash
pytest -q   # behavioral matrix: trivial→0, units→min(N,3), nested→0, ...
```
