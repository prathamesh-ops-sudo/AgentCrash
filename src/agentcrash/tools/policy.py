"""Tool policy enforcement.

Policies are enforced by the tool service before any effect occurs. We start
with exact allowlists and argument validation. A generic LLM judge is never in
the enforcement path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..schemas.policy import PolicyManifest


@dataclass
class Decision:
    allowed: bool
    reason: str = ""
    normalized: dict[str, Any] | None = None

    @property
    def denied(self) -> bool:
        return not self.allowed


class PolicyEnforcer:
    """Evaluate a tool action against a PolicyManifest."""

    def __init__(self, manifest: PolicyManifest | None) -> None:
        self.manifest = manifest

    @property
    def active(self) -> bool:
        return self.manifest is not None

    def decide(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Decision:
        manifest = self.manifest
        if manifest is None:
            # No policy configured: allow all enumerated synthetic operations.
            return Decision(allowed=True, normalized=arguments)

        rule = manifest.rules.get(tool_name)
        if rule is None:
            if manifest.default == "deny":
                return Decision(allowed=False, reason=f"tool {tool_name!r} not allowlisted (default deny)")
            return Decision(allowed=True, normalized=arguments)

        # Argument normalization happens here so enforcement and evaluation see
        # identical canonical values.
        args = {k: v for k, v in (arguments or {}).items()}

        if tool_name == "documents.read":
            doc_id = args.get("document_id")
            if rule.allowed_document_ids is not None and doc_id not in rule.allowed_document_ids:
                return Decision(allowed=False, reason=f"document {doc_id!r} not allowed")
            return Decision(allowed=True, normalized=args)

        if tool_name == "notes.write":
            note_id = args.get("note_id")
            if rule.allowed_note_ids is not None and note_id not in rule.allowed_note_ids:
                return Decision(allowed=False, reason=f"note {note_id!r} not allowed")
            return Decision(allowed=True, normalized=args)

        if tool_name == "mail.send":
            raw_recipients = args.get("recipients", args.get("recipient", []))
            recipients = raw_recipients if isinstance(raw_recipients, list) else [raw_recipients]
            if rule.allowed_recipients is not None:
                for r in recipients:
                    if r not in rule.allowed_recipients:
                        return Decision(
                            allowed=False,
                            reason=f"recipient {r!r} not allowed",
                            normalized={**args, "recipients": recipients},
                        )
            return Decision(allowed=True, normalized={**args, "recipients": recipients})

        # Unknown tool not specifically handled and a rule was supplied: rely on
        # the rule's extra allowances or default-deny.
        if rule.extra.get("allow", False):
            return Decision(allowed=True, normalized=args)
        if manifest.default == "deny":
            return Decision(allowed=False, reason=f"tool {tool_name!r} has no enforceable rule")
        return Decision(allowed=True, normalized=args)