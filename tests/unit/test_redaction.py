"""Redaction tests: seeded secrets must never survive into an export."""
from agentcrash.evidence.redaction import (
    default_redactions,
    export_preview,
    redact,
    redact_known_paths,
)


def test_redact_scales_secret_to_marker():
    data = {"events": [{"payload": {"body": "the token is SECRET_KEY and nothing else"}}]}
    out = redact(data, secrets=["SECRET_KEY"])
    assert "SECRET_KEY" not in str(out)
    assert "REDACTED" in out["events"][0]["payload"]["body"]


def test_redact_recurses_into_nested_structures():
    data = {"a": {"b": [{"c": "prefix abcd-secret suffix"}]}}
    out = redact(data, secrets=["abcd-secret"])
    assert "abcd-secret" not in str(out)
    assert out["a"]["b"][0]["c"].count("REDACTED") >= 1


def test_redact_leaves_keys_structural():
    data = {"SECRET_KEY": "value-with-token", "ok": 1}
    out = redact(data, secrets=["token"])
    # keys are structural and retained; the value is redacted
    assert "SECRET_KEY" in out
    assert out["ok"] == 1


def test_no_secrets_leaves_untouched():
    data = {"message": "hello world", "n": 42}
    assert redact(data, secrets=[]) == data


def test_default_redactions_shape():
    d = default_redactions(secrets=["a", "b"])
    assert d == {"secrets": ["a", "b"]}


def test_redact_known_paths_removes_user():
    out = redact_known_paths("agent went to C:\\Users\\prath\\AppData\\x", user="prath")
    assert "\\Users\\prath" not in out
    out2 = redact_known_paths("used /home/prath/tool", user="prath")
    assert "/home/prath" not in out2


def test_export_preview_reports_counts_and_bytes():
    class FakeEvent:
        def __init__(self, i):
            self.t = f"evt-{i}"
            self.data = "secret stuff abc"

    p = export_preview([FakeEvent(1), FakeEvent(2)], secrets=["abc"])
    assert p["event_count"] == 2
    assert p["bytes_estimate"] > 0
    assert p["secrets_config_redaction"] is True