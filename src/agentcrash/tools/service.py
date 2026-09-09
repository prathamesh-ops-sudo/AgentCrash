"""Synthetic tool service.

The tool plane supports only enumerated synthetic operations: documents.read,
notes.write, mail.send. It is NOT an HTTP forward proxy and does NOT execute
shell commands. An outbound-mail tool writes to a local outbox; a remote
upload writes to a local sink. Observing that sink proves a defined simulated
outcome, not real external contact.

Every executed tool produces authoritative side-effect events with a unique
request ID and an idempotency key so retries cannot duplicate side effects.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..evidence.store import EventStore
from ..schemas.models import EventRecord
from .policy import PolicyEnforcer
from .world import WorldState

TOOL_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "documents.read": {
        "description": "Read the text content of a stored synthetic document.",
        "arguments": '{"document_id": "str", "required": ["document_id"]}',
    },
    "notes.write": {
        "description": "Write content to a named internal note.",
        "arguments": '{"note_id": "str", "content": "any", "required": ["note_id", "content"]}',
    },
    "mail.send": {
        "description": "Send an email to one or more recipients (writes to local synthetic outbox).",
        "arguments": '{"recipients": "list[str] | str", "subject": "str", "body": "str", "required": ["recipients", "subject", "body"]}',
    },
}

EXECUTED_EFFECT_TYPES: set[str] = {"tool.executed", "world.changed"}


@dataclass
class ToolResult:
    ok: bool
    value: Any = None
    error: str | None = None
    request_id: str = ""
    idempotency_key: str = ""
    effect_type: str | None = None  # authoritative effect this call produced


def _event_id() -> str:
    return uuid.uuid4().hex


class ToolService:
    """Owns the synthetic world and produces authoritative side-effect events."""

    def __init__(
        self,
        world: WorldState,
        store: EventStore,
        run_id: str,
        policy: PolicyEnforcer | None = None,
        sequence_bump: Callable[[], int] | None = None,
    ) -> None:
        self.world = world
        self.store = store
        self.run_id = run_id
        self.policy = policy or PolicyEnforcer(None)
        self.effects: list[dict[str, Any]] = []  # (request_id, idempotency_key, effect_type)
        self._seq = sequence_bump or (lambda: 0)
        self._seen_idempotency: dict[str, ToolResult] = {}

    def list_tools(self) -> list[str]:
        return list(TOOL_DESCRIPTIONS.keys())

    def describe(self) -> dict[str, dict[str, str]]:
        return dict(TOOL_DESCRIPTIONS)

    def _emit(self, driver: str, event_type: str, tool_call_id: str | None,
              parent: str | None, payload: dict[str, Any],
              trust: str = "authoritative") -> EventRecord:
        ev = EventRecord(
            run_id=self.run_id,
            event_id=_event_id(),
            sequence=self._seq(),
            timestamp="",
            actor="tool_service",
            event_type=event_type,
            tool_call_id=tool_call_id,
            parent_event_id=parent,
            trust=trust,
            payload=payload,
        )
        self.store.append_event(ev)
        return ev

    def _emit_driver_start(self, driver: str, ev_type: str, tool_call_id: str,
                           payload: dict[str, Any], parent: str | None) -> EventRecord:
        # callers pass actor; we centralize to tool_service for authoritative events
        return self._emit("tool_service", ev_type, tool_call_id, parent, payload)

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        tool_call_id: str,
        parent_event_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> ToolResult:
        """Validate, enforce policy, execute, and record authoritative effects."""
        if idempotency_key and idempotency_key in self._seen_idempotency:
            return self._seen_idempotency[idempotency_key]

        request_id = _event_id()
        ide_key = idempotency_key or request_id
        result = ToolResult(ok=True, request_id=request_id, idempotency_key=ide_key)

        # 1. tool.requested (untrusted request observed)
        self._emit_driver_start(
            "tool_service", "tool.requested", tool_call_id,
            {"tool": tool_name, "arguments": arguments, "request_id": request_id}, parent_event_id,
        )

        # 2. policy decision
        decision = self.policy.decide(tool_name, arguments)
        if decision.denied:
            self._emit_driver_start(
                "tool_service", "policy.decided", tool_call_id,
                {"tool": tool_name, "decision": "deny", "reason": decision.reason,
                 "request_id": request_id, "policy_id": self.policy.manifest.id if self.policy.manifest else None},
                parent_event_id,
            )
            self._emit_driver_start(
                "tool_service", "tool.rejected", tool_call_id,
                {"tool": tool_name, "reason": decision.reason, "request_id": request_id}, parent_event_id,
            )
            result.ok = False
            result.error = "rejected by policy: " + decision.reason
            self._seen_idempotency[ide_key] = result
            return result

        args = decision.normalized or arguments

        # 3. execute the enumerated synthetic operation
        try:
            effect = self._dispatch(tool_name, args)
        except KeyError:
            self._emit_driver_start(
                "tool_service", "tool.rejected", tool_call_id,
                {"tool": tool_name, "reason": f"unknown tool {tool_name!r}", "request_id": request_id}, parent_event_id,
            )
            result.ok = False
            result.error = f"unknown tool {tool_name!r}"
            self._seen_idempotency[ide_key] = result
            return result

        # 4. tool.executed + world.changed (authoritative effects)
        self._emit_driver_start(
            "tool_service", "tool.executed", tool_call_id,
            {"tool": tool_name, "arguments": args, "request_id": request_id, "effect": effect},
            parent_event_id,
        )
        if effect:
            self._emit_driver_start(
                "tool_service", "world.changed", tool_call_id,
                {"tool": tool_name, "request_id": request_id, "delta": effect["delta"]},
                parent_event_id,
            )
        result.value = effect.get("return") if effect else None
        result.effect_type = effect["type"] if effect else None
        self.effects.append({"request_id": request_id, "idempotency_key": ide_key,
                             "effect_type": result.effect_type})
        if result.effect_type:
            self._seen_idempotency[ide_key] = result
        return result

    def _dispatch(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
        if tool_name == "documents.read":
            doc_id = args["document_id"]
            doc = self.world.read_document(doc_id)
            if doc is None:
                raise KeyError(f"document {doc_id!r} not found")
            return {"type": "read", "return": doc.get("content", ""), "delta": {"read": doc_id}}
        if tool_name == "notes.write":
            note_id = args["note_id"]
            self.world.write_note(note_id, args.get("content"))
            return {"type": "note_write", "return": {"ok": True, "note_id": note_id},
                    "delta": {"notes": {note_id: args.get("content")}}}
        if tool_name == "mail.send":
            raw = args.get("recipients", args.get("recipient", []))
            recipients = raw if isinstance(raw, list) else [raw]
            entry = {
                "to": recipients,
                "subject": args.get("subject", ""),
                "body": args.get("body", ""),
            }
            self.world.append_outbox(entry)
            return {"type": "mail_send", "return": {"ok": True, "message_id": _event_id()},
                    "delta": {"outbox_appended": entry}}
        raise KeyError(tool_name)