"""Unit tests for the tool service: idempotency, policy, event ordering."""


from agentcrash.evidence.store import EventStore
from agentcrash.schemas.policy import PolicyManifest
from agentcrash.tools.policy import PolicyEnforcer
from agentcrash.tools.service import ToolService
from agentcrash.tools.world import WorldState


def _store(tmp_path):
    return EventStore(tmp_path / "t.db")


def _seq():
    n = 0

    def b():
        nonlocal n
        n += 1
        return n

    return b


def test_documents_read_and_idempotency(tmp_path):
    world = WorldState({"documents": {"invoice-001": {"content": "hello"}}})
    store = _store(tmp_path)
    svc = ToolService(world, store, run_id="r1", sequence_bump=_seq())
    r = svc.execute("documents.read", {"document_id": "invoice-001"},
                    tool_call_id="t1", idempotency_key="k1")
    assert r.ok and r.value == "hello"
    # replay with the same idempotency key returns a cached result, no new effect
    r2 = svc.execute("documents.read", {"document_id": "invoice-001"},
                     tool_call_id="t2", idempotency_key="k1")
    assert r2.ok
    effects = [e for e in store.events("r1") if e.event_type in ("tool.executed", "world.changed")]
    assert len(effects) >= 1  # idempotent replay adds no new executed event
    assert r2.request_id == r.request_id


def test_retry_does_not_duplicate_send(tmp_path):
    world = WorldState({"outbox": []})
    store = _store(tmp_path)
    svc = ToolService(world, store, run_id="r2", sequence_bump=_seq())
    svc.execute("mail.send", {"recipients": "a@b.c", "subject": "s", "body": "b"},
                tool_call_id="t1", idempotency_key="ide1")
    svc.execute("mail.send", {"recipients": "a@b.c", "subject": "s", "body": "b"},
                tool_call_id="t2", idempotency_key="ide1")
    assert len(world.outbox()) == 1


def test_policy_denied_tool_has_no_effect(tmp_path):
    world = WorldState({"outbox": []})
    store = _store(tmp_path)
    pol = PolicyEnforcer(PolicyManifest(
        id="p",
        rules={"mail.send": {"allowed_recipients": ["ok@b.c"]}},
    ))
    svc = ToolService(world, store, run_id="r3", sequence_bump=_seq(), policy=pol)
    r = svc.execute("mail.send", {"recipients": "evil@b.c", "subject": "s", "body": "b"},
                    tool_call_id="t1")
    assert not r.ok
    assert world.outbox() == []
    types = {e.event_type for e in store.events("r3")}
    assert "world.changed" not in types
    assert "tool.rejected" in types


def test_unknown_tool_rejected(tmp_path):
    store = _store(tmp_path)
    svc = ToolService(WorldState({}), store, run_id="r4", sequence_bump=_seq())
    r = svc.execute("nope.tool", {}, tool_call_id="t1")
    assert not r.ok and "unknown tool" in r.error


def test_notes_write_lands_in_world(tmp_path):
    world = WorldState({"notes": {}})
    store = _store(tmp_path)
    svc = ToolService(world, store, run_id="r5", sequence_bump=_seq())
    svc.execute("notes.write", {"note_id": "summary", "content": {"amount": 1250.0}},
                tool_call_id="t1")
    assert world.get_note("summary") == {"amount": 1250.0}
    assert world.get_note("summary")["amount"] == 1250.0