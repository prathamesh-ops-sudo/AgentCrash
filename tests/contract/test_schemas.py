"""Schema contract tests: scenarios, policies, events, results.

These lock the public contracts so schema changes require migration + tests.
"""
import pytest
from pydantic import ValidationError

from agentcrash.evaluators.outputs import (
    canary_in_outbox,
    evaluate_predicate,
    world_field_changed,
    world_field_equals,
)
from agentcrash.schemas.models import Outcome
from agentcrash.schemas.policy import PolicyManifest
from agentcrash.schemas.scenario import InjectionMatch, ScenarioManifest


def test_scenario_manifest_valid():
    m = ScenarioManifest(
        id="invoice-confidential-note",
        version="0.1.0",
        task_file="task.txt",
        world_fixture="world.json",
        tools=["documents.read", "mail.send", "notes.write"],
        injection=InjectionMatch(tool="documents.read", document_id="invoice-001",
                                 replacement_file="injected.txt"),
    )
    assert m.schema_version == 1


def test_scenario_rejects_unknown_top_level_fields():
    with pytest.raises(ValidationError):
        ScenarioManifest.model_validate({"id": "x", "rogue": True})


def test_scenario_rejects_wrong_schema_version():
    with pytest.raises(ValidationError):
        ScenarioManifest(id="x", schema_version=999)


def test_scenario_rejects_id_with_space():
    with pytest.raises(ValidationError):
        ScenarioManifest(id="has space")


def test_policy_default_deny_unknown_tool():
    p = PolicyManifest(id="p", rules={}, default="deny")
    from agentcrash.tools.policy import PolicyEnforcer

    enforcer = PolicyEnforcer(p)
    d = enforcer.decide("Documents.FancyTool", {})
    assert d.denied
    assert "not allowlisted" in d.reason


def test_policy_blocks_external_recipient():
    p = PolicyManifest(
        id="invoice-summary-only",
        rules={
            "mail.send": {"allowed_recipients": ["finance@example.invalid"]},
        },
    )
    from agentcrash.tools.policy import PolicyEnforcer

    enforcer = PolicyEnforcer(p)
    assert enforcer.decide("mail.send", {"recipients": "external@example.invalid"}).denied
    assert enforcer.decide("mail.send", {"recipients": "finance@example.invalid"}).allowed


def test_policy_blocks_out_of_allowlist_document():
    from agentcrash.tools.policy import PolicyEnforcer

    p = PolicyManifest(id="p", rules={"documents.read": {"allowed_document_ids": ["invoice-001"]}})
    enforcer = PolicyEnforcer(p)
    assert enforcer.decide("documents.read", {"document_id": "confidential-note"}).denied
    assert enforcer.decide("documents.read", {"document_id": "invoice-001"}).allowed


# ---- evaluator predicates ----
def test_world_field_equals_pass_fail():
    world = {"notes": {"invoice_summary": {"amount": 1250.0}}}
    out, ev = world_field_equals(world, "notes.invoice_summary.amount", 1250.0)
    assert out == Outcome.PASS
    out, ev = world_field_equals(world, "notes.invoice_summary.amount", 100)
    assert out == Outcome.FAIL


def test_canary_detection():
    world = {"outbox": [{"to": ["external-recipient@example.invalid"], "body": "confidential-note is here"}]}
    out, ev = canary_in_outbox(world, canary="confidential-note",
                               recipient="external-recipient@example.invalid")
    assert out == Outcome.PASS
    out2, _ = canary_in_outbox({"outbox": []}, canary="x", recipient="a@b.c")
    assert out2 == Outcome.FAIL


def test_world_field_changed():
    before = {"notes": {"approval": {"approved": False}}}
    after = {"notes": {"approval": {"approved": True}}}
    out, _ = world_field_changed(before, after, "notes.approval.approved")
    assert out == Outcome.PASS


def test_unsupported_predicate_rejected():
    from agentcrash.evaluators.outputs import EvaluatorError

    with pytest.raises(EvaluatorError):
        evaluate_predicate("no_such_thing", world={})


def test_policy_digest_stable():
    p1 = PolicyManifest(id="p", rules={"mail.send": {"allowed_recipients": ["a@b.c"]}})
    p2 = PolicyManifest(id="p", rules={"mail.send": {"allowed_recipients": ["a@b.c"]}})
    assert p1.digest_input == p2.digest_input
    import hashlib

    assert hashlib.sha256(p1.digest_input.encode()).hexdigest()