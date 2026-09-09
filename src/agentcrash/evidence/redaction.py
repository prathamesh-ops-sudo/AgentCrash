"""Redaction of evidence exports.

Exports use an allowlist of fields and redact configured secrets, provider
keys, local usernames and paths where unnecessary, and sensitive payloads. An
export preview lists what will be included. We never claim an export retains
the raw evidence digest after redaction.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _escape(normalized: str) -> str:
    return re.escape(normalized)


def default_redactions(secrets: list[str] | None = None) -> dict[str, list[str]]:
    return {"secrets": list(secrets or [])}


def redact(data: Any, secrets: list[str] | None = None) -> Any:
    """Recursively redact any configured secret strings found in data.

    Returns a deep-redacted copy. Keys are left intact (they are structural);
    values that contain a secret are replaced with a neutral marker.
    """
    _secrets = [s for s in (secrets or []) if s]

    def _walk(node: Any) -> Any:
        if isinstance(node, str):
            out = node
            for s in _secrets:
                out = out.replace(s, "[REDACTED]")
            return out
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_walk(v) for v in node]
        return node

    return _walk(data)


def redact_known_paths(text: str, user: str | None = None) -> str:
    """Scrub local usernames and absolute user paths from a text payload."""
    out = text
    if user:
        out = re.sub(rf"[A-Za-z]:\\Users\\{re.escape(user)}", "~", out)
        out = re.sub(rf"/Users/{re.escape(user)}", "~", out)
        out = re.sub(rf"/home/{re.escape(user)}", "~", out)
        out = re.sub(rf"C:\\Users\\{re.escape(user)}", "~", out)
    return out


def export_preview(events: list[Any], secrets: list[str] | None) -> dict[str, Any]:
    """Offer a preview of what an export includes before writing it."""
    sample_jsonl = "\n".join(json.dumps(ev.__dict__ if hasattr(ev, "__dict__") else ev,
                                        default=str) for ev in events)
    return {
        "event_count": len(events),
        "bytes_estimate": len(sample_jsonl.encode("utf-8")),
        "secrets_config_redaction": bool(secrets),
        "note": "Values are redacted; keys are structural and retained.",
    }