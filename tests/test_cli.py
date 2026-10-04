"""CLI surface tests."""

import json
import subprocess
import sys
from pathlib import Path

from devin_orchestrator.cli import main


def test_plan_command_prints_json(capsys):
    rc = main(["plan", '{"kind":"implementation","independent_units":2}'])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["workers"] == 2
    assert out["collect"] is True


def test_plan_from_file(tmp_path, capsys):
    spec = tmp_path / "spec.json"
    spec.write_text('{"kind":"refactor","estimated_scope":"large","independent_units":5}')
    rc = main(["plan", "--spec-file", str(spec)])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["workers"] == 3


def test_bad_spec_returns_2(capsys):
    assert main(["plan", "{bad"]) == 2
    assert "error:" in capsys.readouterr().err


def test_plan_explain_and_schema(capsys):
    from devin_orchestrator.cli import main
    assert main(["plan", '{"kind":"question"}', "--explain"]) == 0
    out = capsys.readouterr().out
    assert "0 worker(s)" in out and "inline" in out
    assert main(["schema", "spec"]) == 0
    import json as j
    assert "task spec" in j.loads(capsys.readouterr().out)["title"]


def test_record_and_history(tmp_path, capsys):
    reg = tmp_path / "plans.jsonl"
    assert main(["record", '{"workers":[1,2],"mode":"parallel"}',
                 "--outcome", "success", "--registry", str(reg)]) == 0
    assert main(["record", '{"workers":[1]}',
                 "--outcome", "failed", "--registry", str(reg)]) == 0
    capsys.readouterr()
    assert main(["history", "--registry", str(reg), "--json"]) == 0
    import json
    out = json.loads(capsys.readouterr().out)
    assert out["total"] == 2
    assert out["by_outcome"] == {"success": 1, "failed": 1}
    assert "nothing leaves the machine" in out["note"]


def test_record_bad_outcome(tmp_path, capsys):
    import pytest
    with pytest.raises(SystemExit):  # argparse rejects invalid choices
        main(["record", "{}", "--outcome", "bogus",
              "--registry", str(tmp_path / "p.jsonl")])


def test_history_empty(tmp_path, capsys):
    assert main(["history", "--registry", str(tmp_path / "nope.jsonl")]) == 0
    assert "none" in capsys.readouterr().out
