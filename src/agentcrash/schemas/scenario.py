"""Scenario manifest contract (schema version 1).

A scenario pack is a data-only directory. The manifest below is the public
contract; all runtime inputs (task, world fixture, injected content) are kept
in separate fixture files so the manifest stays readable. The scenario loader
validates and resolves these into a Scenario object before any run.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import SCHEMA_VERSION


class InjectionMatch(BaseModel):
    """How to locate the document that the injection replaces."""
    tool: str = "documents.read"
    document_id: str = ""
    replacement_file: str = ""


class EvaluatorSpec(BaseModel):
    utility: dict[str, Any] = Field(default_factory=dict)
    security: dict[str, Any] = Field(default_factory=dict)


class ScenarioLimit(BaseModel):
    max_tool_calls: int = Field(default=20, ge=1)
    timeout_seconds: int = Field(default=120, ge=1)


class ScenarioManifest(BaseModel):
    """Public scenario contract. `schema_version` is validated at load."""

    model_config = ConfigDict(extra="forbid")  # unknown top-level fields rejected

    schema_version: int = SCHEMA_VERSION
    id: str
    version: str = "0.1.0"
    title: str = ""
    description: str = ""
    license: str = "Apache-2.0"
    author: str = ""
    mode: Literal["synthetic"] = "synthetic"
    task_file: str = ""
    world_fixture: str = "world.json"
    injection: InjectionMatch | None = None
    tools: list[str] = Field(default_factory=list)
    limits: ScenarioLimit = Field(default_factory=ScenarioLimit)
    evaluators: EvaluatorSpec = Field(default_factory=EvaluatorSpec)
    benign_trace: str | None = None      # expected benign scripted trace
    attack_trace: str | None = None      # expected vulnerable scripted trace
    blocked_trace: str | None = None     # expected blocked scripted trace
    attribution: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def _version_ok(cls, v: int) -> int:
        if v != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema version {v}; this build supports {SCHEMA_VERSION}"
            )
        return v

    @field_validator("id")
    @classmethod
    def _id_ok(cls, v: str) -> str:
        if not v or " " in v:
            raise ValueError(f"scenario id must be non-empty and without spaces: {v!r}")
        return v


class ScenarioLoadError(Exception):
    """Raised when a scenario pack is malformed or unsafe to load."""


class Scenario:
    """Resolved, validated scenario pack with fixture content in memory."""

    def __init__(
        self,
        manifest: ScenarioManifest,
        basedir: str,
        task_text: str,
        world: dict[str, Any],
        injection_content: str | None,
        benign_trace: list[dict[str, Any]],
        attack_trace: list[dict[str, Any]],
        blocked_trace: list[dict[str, Any]],
    ) -> None:
        self.manifest = manifest
        self.basedir = basedir
        self.task_text = task_text
        self.world = world
        self.injection_content = injection_content
        self.benign_trace = benign_trace
        self.attack_trace = attack_trace
        self.blocked_trace = blocked_trace

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def version(self) -> str:
        return self.manifest.version