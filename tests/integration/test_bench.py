"""Integration tests: full runs against the shipped scenario packs using the
deterministic scripted model. These constitute the scenario bench: for each
pack, the benign variant must be clean and the attack variant must exercise the
forbidden effect, while the policy-blocked variant must stop it while preserving
utility.

This is a deterministic, offline suite (no provider, no network).
"""
import pathlib

import pytest

from agentcrash.core.policies import load_policy
from agentcrash.core.runner import Runner
from agentcrash.evidence.store import BlobStore, EventStore
from agentcrash.schemas.models import RunConfig

SCENARIOS = pathlib.Path(__file__).resolve().parents[2] / "scenarios"
POLICY = pathlib.Path(__file__).resolve().parents[2] / "examples" / "policies" / "invoice-summary-only.yaml"

# scenario_id -> (security_predicate_name, policy_that_blocks_outside_default)
BENCH = {
    "invoice-confidential-note": "canary_in_outbox",
    "support-tenant-boundary": "read_attempted",
    "document-write-redirection": "world_field_changed",
    "tool-response-instruction": "canary_in_outbox",
    "persistent-note-poisoning": "world_field_equals",
}


def _run(scenario, variant, policy=None, data_dir=None):
    store = EventStore(data_dir / "t.db") if data_dir else EventStore(":memory:")
    blobs = BlobStore(data_dir / "blobs") if data_dir else BlobStore(data_dir or ".")
    cfg = RunConfig(scenario_id=scenario, variant=variant,
                    policy_id=policy.id if policy else None)
    r = Runner(store, blobs, str(SCENARIOS), cfg, policy=policy)
    dims = r.execute()
    return dims, store, r


@pytest.mark.parametrize("scenario", list(BENCH))
def test_benign_is_clean(tmp_path, scenario):
    dims, _, _ = _run(scenario, "benign", data_dir=tmp_path)
    assert dims.task_success is True
    assert dims.attack_attempted is False
    assert dims.attack_succeeded is False
    assert dims.completeness is True


@pytest.mark.parametrize("scenario", list(BENCH))
def test_attack_exercises_forbidden_effect(tmp_path, scenario):
    dims, _, _ = _run(scenario, "attack", data_dir=tmp_path)
    assert dims.task_success is True
    assert dims.attack_attempted is True
    assert dims.attack_succeeded is True
    assert dims.completeness is True


def test_flagged_invoice_policy_blocks_attack_keeps_utility(tmp_path):
    policy = load_policy(POLICY)
    vulnerable = _run("invoice-confidential-note", "attack", data_dir=tmp_path)[0]
    defended = _run("invoice-confidential-note", "attack", policy=policy,
                    data_dir=tmp_path)[0]
    assert vulnerable.attack_succeeded is True
    assert defended.attack_succeeded is False
    # utility is preserved by a good policy, so 'block everything' is visibly
    # distinct from a working fix
    assert defended.task_success is True
    assert defended.policy_blocked is True


def test_rerun_creates_fresh_world(tmp_path):
    """A rerun starts from the immutable fixture: no state leaks between runs."""
    d1, s1, r1 = _run("invoice-confidential-note", "attack", data_dir=tmp_path)
    d2, s2, r2 = _run("invoice-confidential-note", "attack", data_dir=tmp_path)
    assert r1.run_id != r2.run_id
    # both runs independently reach the same dimensions (deterministic)
    assert d1.summary() == d2.summary()