# devin-control

<!-- DEVIN-ECO:BEGIN -->
> **Part of the [DEVIN ecosystem](https://github.com/Icaro0310/awesome-devin)**  
> Track: Control · Nature: product  
> For: Security engineers, AI engineers  
> Interface: CLI / Bridge  
> Path: AI engineers · step 1/3 — before `devin-orchestrator`
<!-- DEVIN-ECO:END -->

Control how Devin runs: a policy-gated ACP bridge, a background-worker
fan-out planner, config profile switching, and a live activity board —
the write/control side of the ecosystem.

| Package | Registry | What it does |
|---|---|---|
| [`packages/bridge`](packages/bridge) | `@icaro0310/devin-bridge` (npm) | Cross-platform policy-gated ACP bridge for Devin CLI — isolated sessions per project with fail-closed permission rules |
| [`packages/orchestrator`](packages/orchestrator) | `devin-fanout` (PyPI) | Background-worker fan-out policy: deterministic planner enforcing worker caps, no nesting, collect-before-report |
| [`packages/switch`](packages/switch) | `devin-switch` (PyPI) | Switch between Devin configuration profiles (hooks, MCP, models) with snapshot and verification |
| [`packages/office`](packages/office) | source-only | Live Devin activity as an animated SVG circuit board: sessions, subagents, tools |

> **Renamed (Oct 2026):** this repository moved from `Icaro0310/devin-bridge` to `Icaro0310/devin-control` when it became the `devin-control` product workspace. The npm package `@icaro0310/devin-bridge`, the PyPI packages and all console scripts keep their names; stars, issues and history are preserved by the redirect.

## Layout

```
packages/<name>/   one installable package each — bridge is Node (npm),
                   orchestrator/switch are Python (uv workspace), office
                   is a source-only service (flat modules, PYTHONPATH).
```

Each package ships independently: a tag `orchestrator-vX.Y.Z` or
`switch-vX.Y.Z` publishes only that PyPI package; a `bridge-vX.Y.Z` tag
creates a GitHub Release that publishes `@icaro0310/devin-bridge` to
npmjs and GitHub Packages. CI is scoped per path — a change under
`packages/switch/` runs only the switch suite.

The standalone `devin-orchestrator`, `devin-switch` and `devin-office`
repositories were absorbed into this workspace (F4.4); their histories
are preserved under `packages/` and the old repos are archived with
pointers here.

## Platform support

All packages support Linux and Windows (office is Linux-only — it uses
`fcntl`; macOS support is planned, not claimed). Per-package guides live
under `packages/<name>/`.

> **Unofficial community project.** Not affiliated with, endorsed by, or
> sponsored by Cognition AI. "Devin" is a trademark of Cognition AI.
