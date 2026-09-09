"""Tool policy contract (schema version 1).

Policies are enforced by the tool service before any effect occurs. The
default stance is explicit deny; unknown constructs fail configuration
validation rather than being silently ignored.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from . import SCHEMA_VERSION


class ToolRule(BaseModel):
    allowed_document_ids: list[str] | None = None
    allowed_note_ids: list[str] | None = None
    allowed_recipients: list[str] | None = None
    allowed_fields: list[str] | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class PolicyManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    id: str
    description: str = ""
    rules: dict[str, ToolRule] = Field(default_factory=dict)
    default: str = "deny"

    @property
    def digest_input(self) -> str:
        """Canonical serialization for policy-diff computation."""
        import json

        return json.dumps(
            {
                "id": self.id,
                "rules": {
                    k: v.model_dump(exclude_none=True) for k, v in self.rules.items()
                },
                "default": self.default,
            },
            sort_keys=True,
        )


class PolicyParseError(Exception):
    pass