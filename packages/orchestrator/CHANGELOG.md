# Changelog

## [Unreleased]

### Changed

- README gains the generated `Part of the DEVIN ecosystem` block
  (track/nature/audience/interface rendered from the registry).

- `labeler.yml` is now a thin caller of the shared reusable workflow in `devin-powerups` (`@v1`); PR labeling behavior is unchanged.

- Install section now recommends pypi `uv tool install devin-fanout` (CLI stays `devin-orchestrator`) as the primary route, with `pipx`/source installs documented as alternatives.

### Fixed

- `devin_orchestrator.__version__` now reports `0.2.0`, matching
  `[project].version` in `pyproject.toml`; a `test_version.py` guard and
  the publish workflow's wheel check keep the two in sync.

## 0.2.0

- Merged the unpublished `devin-subagent-orchestrator` draft into this repo.
- SKILL.md rewritten: full policy (session-start triage, worker bounds, profiles,
  `.sessions.json` reuse, collection contract, worktree protection, publication
  gate) integrated with the deterministic planner step.
- Added `evals/evals.json` fixtures and `tests/test_skill_policy.py`.

## 0.1.0

- Initial release: deterministic fan-out planner, skill, always-on rule.
