"""Result dimensions and shared value objects for AgentCrash.

These are the machine-readable truth for what a run means. Keep result
dimensions separate: task utility and security outcome are computed
independently and never collapse into one score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from . import SCHEMA_VERSION


class RunMode(StrEnum):
    RECORDED = "recorded"
    LIVE = "live"
    COUNTERFACTUAL = "counterfactual"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Outcome(StrEnum):
    """Evaluator outcome for a single predicate."""

    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


@dataclass
class RunResultDimensions:
    """Separated utility and security result dimensions."""

    task_success: bool | None = None  # utility_pass
    attack_attempted: bool | None = None
    attack_succeeded: bool | None = None  # attacker goal in authoritative state
    policy_blocked: bool | None = None
    completeness: bool = False  # required evidence present

    def summary(self) -> dict[str, Any]:
        return {
            "task_success": self.task_success,
            "attack_attempted": self.attack_attempted,
            "attack_succeeded": self.attack_succeeded,
            "policy_blocked": self.policy_blocked,
            "completeness": self.completeness,
        }


@dataclass
class EventRecord:
    """One recorded event in the authoritative event store.

    Fields mirror the public event contract. `trust` marks authoritative
    (tool-service / supervisor) events vs untrusted guest-emitted lines.
    """

    schema_version: int = SCHEMA_VERSION
    run_id: str = ""
    event_id: str = ""
    sequence: int = 0
    timestamp: str = ""
    actor: str = ""  # supervisor | tool_service | worker | broker | evaluator
    event_type: str = ""
    tool_call_id: str | None = None
    parent_event_id: str | None = None
    payload_ref: str | None = None
    payload_digest: str | None = None
    trust: str = "authoritative"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunConfig:
    """Declarative run selection. Immutable once a run starts."""

    scenario_id: str = ""
    scenario_version: str = ""
    variant: str = "attack"  # benign | attack
    adapter: str = "reference"
    policy_id: str | None = None
    trials: int = 1
    model: str = "scripted"
    provider: str | None = None
    mode: RunMode = RunMode.LIVE
    max_tool_calls: int = 20
    timeout_seconds: int = 120


@dataclass
class TrialGroupMeta:
    """Metadata needed to align comparable runs for `compare`."""

    scenario_version: str = ""
    adapter_digest: str = ""
    policy_digest: str | None = None
    model_identity: str = ""
    trial_index: int = 0

    def alignment_warnings(self, other: TrialGroupMeta) -> list[str]:
        warnings: list[str] = []
        if self.scenario_version != other.scenario_version:
            warnings.append("scenario version differs")
        if self.adapter_digest != other.adapter_digest:
            warnings.append("adapter digest differs")
        if self.policy_digest != other.policy_digest:
            warnings.append("policy digest differs")
        if self.model_identity != other.model_identity:
            warnings.append("model identity differs")
        return warnings