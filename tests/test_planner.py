"""Behavioral matrix for the fan-out planner — no workers are spawned."""

import json

import pytest

from devin_orchestrator.planner import MAX_WORKERS, plan_task, plan_task_json


# -- required matrix -------------------------------------------------------

def test_trivial_task_spawns_zero_workers():
    plan = plan_task({"kind": "fix", "estimated_scope": "trivial"})
    assert plan.workers == 0
    assert plan.mode == "none"


def test_question_spawns_zero_workers():
    plan = plan_task({"kind": "question"})
    assert plan.workers == 0


def test_single_unit_small_work_stays_inline():
    plan = plan_task(
        {"kind": "implementation", "independent_units": 1, "estimated_scope": "small"}
    )
    assert plan.workers == 0


def test_two_independent_units_get_two_workers():
    plan = plan_task(
        {
            "kind": "implementation",
            "independent_units": 2,
            "needs_write": True,
            "estimated_scope": "medium",
            "summary": "API + UI",
        }
    )
    assert plan.workers == 2
    assert plan.mode == "background"
    assert plan.profiles == ["subagent_general", "subagent_general"]
    assert plan.collect is True  # parent must gather results


def test_many_units_capped_at_max():
    plan = plan_task(
        {"kind": "implementation", "independent_units": 8, "estimated_scope": "large"}
    )
    assert plan.workers == MAX_WORKERS
    assert "capped" in plan.rationale


def test_large_refactor_bounded():
    plan = plan_task({"kind": "refactor", "independent_units": 1, "estimated_scope": "large"})
    assert 1 <= plan.workers <= MAX_WORKERS


def test_nested_fanout_blocked():
    plan = plan_task(
        {"kind": "implementation", "independent_units": 3},
        env={"DEVIN_INSIDE_SUBAGENT": "1"},
    )
    assert plan.workers == 0
    assert plan.nesting_blocked is True
    assert plan.warnings


def test_review_forces_readonly_profile():
    plan = plan_task(
        {"kind": "review", "independent_units": 2, "needs_write": True}
    )
    assert all(p == "subagent_explore" for p in plan.profiles)
    assert plan.warnings  # needs_write mismatch flagged


def test_env_cap_can_only_lower():
    plan = plan_task(
        {"kind": "implementation", "independent_units": 3},
        env={"DEVIN_MAX_WORKERS": "2"},
    )
    assert plan.workers == 2
    plan = plan_task(
        {"kind": "implementation", "independent_units": 3},
        env={"DEVIN_MAX_WORKERS": "99"},
    )
    assert plan.workers == MAX_WORKERS


# -- contract / safety -----------------------------------------------------

def test_plan_is_data_only():
    """The plan must carry no actionable paths, URLs or commands."""
    out = json.loads(
        plan_task_json(
            '{"kind":"implementation","independent_units":3,"summary":"x","needs_write":true}'
        )
    )
    blob = json.dumps(out)
    for forbidden in ("http://", "https://", "C:\\", "/home/", "git ", "gh "):
        assert forbidden not in blob
    assert out["limits"]["nesting"] == "forbidden"


def test_every_fanned_plan_requires_collection():
    for units in (2, 3, 5):
        plan = plan_task({"kind": "implementation", "independent_units": units})
        assert plan.collect is True, units


def test_invalid_specs_rejected():
    with pytest.raises(ValueError):
        plan_task("not a dict")
    with pytest.raises(ValueError):
        plan_task({"kind": "hack"})
    with pytest.raises(ValueError):
        plan_task({"kind": "implementation", "independent_units": -1})
    with pytest.raises(ValueError):
        plan_task({"kind": "implementation", "independent_units": True})
    with pytest.raises(ValueError):
        plan_task({"kind": "implementation", "estimated_scope": "huge"})
    with pytest.raises(ValueError):
        plan_task_json("{invalid json")
