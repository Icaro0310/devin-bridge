# Changelog

## [Unreleased]

### Changed

- `labeler.yml` is now a thin caller of the shared reusable workflow in `devin-powerups` (`@v1`); PR labeling behavior is unchanged.

- Install section now recommends pypi `uv tool install devin-fanout` (CLI stays `devin-orchestrator`) as the primary route, with `pipx`/source installs documented as alternatives.

## 0.2.0

- Merged the unpublished `devin-subagent-orchestrator` draft into this repo.
- SKILL.md rewritten: full policy (session-start triage, worker bounds, profiles,
  `.sessions.json` reuse, collection contract, worktree protection, publication
  gate) integrated with the deterministic planner step.
- Added `evals/evals.json` fixtures and `tests/test_skill_policy.py`.

## 0.1.0

- Initial release: deterministic fan-out planner, skill, always-on rule.
