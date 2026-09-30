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
