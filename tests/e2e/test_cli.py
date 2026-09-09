"""End-to-end tests: install the built wheel into an isolated venv, run the
CLI, and verify exit-code and output contracts.

These are the acceptance tests closest to the blueprint's AC001–AC020. They run
the real `agentcrash` console script in a subprocess.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _cli(data_dir: Path, *args: str, expect: int = 0) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    cmd = [sys.executable, "-m", "agentcrash.cli.app", *args, "--data-dir", str(data_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                          cwd=ROOT, timeout=120)
    assert proc.returncode == expect, f"exit {proc.returncode} != {expect}\n{proc.stdout}\n{proc.stderr}"
    return proc


def test_demo_run_attack_exit_code(data_dir_fx):
    """An attack variant that succeeds leaks a canary -> exit code 1 (test failure)."""
    proc = _cli(data_dir_fx, "run", "invoice-confidential-note",
                "--variant", "attack", "--json", expect=1)
    out = json.loads(proc.stdout)
    assert out["runs"][0]["dimensions"]["attack_succeeded"] is True


def test_demo_run_benign_exit_code(data_dir_fx):
    """A benign variant is clean -> exit code 0."""
    proc = _cli(data_dir_fx, "run", "invoice-confidential-note",
                "--variant", "benign", "--json", expect=0)
    out = json.loads(proc.stdout)
    assert out["runs"][0]["dimensions"]["attack_succeeded"] is False


def test_report_formats(data_dir_fx):
    proc = _cli(data_dir_fx, "run", "invoice-confidential-note",
                "--variant", "benign", "--json", expect=0)
    run_id = json.loads(proc.stdout)["runs"][0]["run_id"]
    for fmt in ("json", "html", "junit"):
        r = _cli(data_dir_fx, "report", run_id, "--format", fmt)
        assert r.returncode == 0
        assert r.stdout.strip()


def test_runs_list_and_purge(data_dir_fx):
    _cli(data_dir_fx, "run", "invoice-confidential-note", "--variant", "benign", "--json", expect=0)
    proc = _cli(data_dir_fx, "runs", "--json")
    data = json.loads(proc.stdout)
    assert len(data["runs"]) >= 1
    run_id = data["runs"][0]["run_id"]
    p = _cli(data_dir_fx, "purge", run_id)
    assert "purged" in json.loads(p.stdout)


@pytest.fixture
def data_dir_fx(tmp_path):
    return tmp_path