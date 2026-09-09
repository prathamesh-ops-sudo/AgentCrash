"""Run planner and lifecycle orchestrator.

Startup sequence: validate, preflight, allocate, instantiate, execute,
evaluate, redact, finalize, clean up. Teardown runs in a finally path. Retained
evidence is separate from disposable execution state.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any

from ..adapters.protocol import AgentResult
from ..broker.models import BrokerError, BudgetEnforcer, Decision, ScriptedBroker
from ..core.loader import load_scenario
from ..evaluators.runner import EvaluatorRunner
from ..evidence.store import BlobStore, EventStore
from ..schemas.models import (
    EventRecord,
    Outcome,
    RunConfig,
    RunResultDimensions,
    RunStatus,
)
from ..schemas.policy import PolicyManifest
from ..schemas.scenario import Scenario
from ..tools.policy import PolicyEnforcer
from ..tools.service import ToolService
from ..tools.world import WorldState

RUN_NS = "agentcrash-run"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _trace_decisions(trace: list[dict]) -> list[Decision]:
    """Build a list of Decisions from a trace JSON list of decision dicts."""
    out = []
    for d in trace:
        kind = d.get("kind", "tool_call")
        if kind == "answer":
            out.append(Decision(kind="answer", text=d.get("text", "")))
        else:
            out.append(Decision(
                kind="tool_call",
                tool_name=d.get("tool_name"),
                arguments=d.get("arguments"),
                tool_call_id=d.get("tool_call_id"),
            ))
    return out


def _seq_counter():
    n = 0

    def bump() -> int:
        nonlocal n
        n += 1
        return n

    return bump


@dataclass
class RunHandle:
    run: Runner
    result: Any = None


class Runner:
    """One run of one scenario/variant/trial. Fresh world per trial."""

    def __init__(
        self,
        store: EventStore,
        blobs: BlobStore,
        scenarios_root: str,
        config: RunConfig,
        policy: PolicyManifest | None = None,
        adapter_factory=None,
    ) -> None:
        self.store = store
        self.blobs = blobs
        self.scenarios_root = scenarios_root
        self.config = config
        self.policy_manifest = policy
        self.adapter_factory = adapter_factory
        self.run_id = uuid.uuid4().hex
        self.status = RunStatus.PENDING
        self.dims: RunResultDimensions | None = None
        self.results: dict[str, tuple[Outcome, str]] = {}

    # ------------------------------------------------------------------ #
    def execute(self) -> RunResultDimensions:
        """Synchronous wrapper around the async lifecycle (for CLI/tests)."""
        return asyncio.run(self.run())

    # ------------------------------------------------------------------ #
    async def run(self) -> RunResultDimensions:
        seq = _seq_counter()
        self.status = RunStatus.RUNNING
        self.store.record_run(
            self.run_id, self.config.scenario_id, self.config.scenario_version,
            self.config.variant, self.config.adapter, self.config.model,
            self.config.policy_id, "running", _now(),
        )

        # validate + preflight
        scenario = load_scenario(f"{self.scenarios_root}/{self.config.scenario_id}")
        # fresh immutable world from fixture
        world = WorldState(scenario.world)
        before = world.snapshot()

        # authoritative supervisor event: run.started
        self.store.append_event(EventRecord(
            run_id=self.run_id, event_id=uuid.uuid4().hex, sequence=seq(),
            timestamp=_now(), actor="supervisor", event_type="run.started",
            payload={
                "scenario_id": scenario.id, "scenario_version": scenario.version,
                "variant": self.config.variant, "adapter": self.config.adapter,
                "policy_id": self.config.policy_id, "model": self.config.model,
                "mode": self.config.mode.value,
            },
        ))

        # allocate: tool service + policy + world, blobs for payload refs
        policy = PolicyEnforcer(self.policy_manifest)
        tools = ToolService(world, self.store, self.run_id, policy=policy,
                            sequence_bump=seq)

        # determine the adapter's tool client (scope: policy enforced server-side)
        tool_wrappers = {
            name: _make_tool_fn(tools, name)
            for name in tools.list_tools()
        }

        # inject the untrusted content for attack variant
        trace = self._select_trace(scenario)
        inj = scenario.manifest.injection
        if self.config.variant == "attack" and scenario.injection_content is not None and inj:
            world.set_document(inj.document_id, scenario.injection_content)

        # instantiate model broker
        broker = ScriptedBroker(trace=trace, identity=f"scripted/{self.config.model}")
        budget = BudgetEnforcer(max_calls=scenario.manifest.limits.max_tool_calls)

        cancelled = asyncio.Event()
        context = _Context(
            task=scenario.task_text,
            tools=tool_wrappers,
            model=broker,
            budget=budget,
            cancelled=cancelled,
        )

        # execute: reference adapter reads synthetic tool events as primary record
        adapter = (self.adapter_factory or _default_adapter)()
        agent_result: AgentResult = await _run_guard(adapter, context, scenario)

        # agent.completed
        self.store.append_event(EventRecord(
            run_id=self.run_id, event_id=uuid.uuid4().hex, sequence=seq(),
            timestamp=_now(), actor="worker", event_type="agent.completed",
            payload={"final_output": agent_result.final_output,
                     "finish_reason": agent_result.finish_reason,
                     "tool_calls": agent_result.tool_calls_made},
        ))

        # evaluate (predicates + non-completeness dimensions)
        evaluator = EvaluatorRunner(self.store)
        after = world.snapshot()
        dims, results = evaluator.evaluate(self.run_id, scenario, after, before)
        self.results = results

        # evaluator.completed (authoritative)
        self.store.append_event(EventRecord(
            run_id=self.run_id, event_id=uuid.uuid4().hex, sequence=seq(),
            timestamp=_now(), actor="evaluator", event_type="evaluator.completed",
            payload={"dimensions": dims.summary(),
                     "predicates": {k: [o.value, e] for k, (o, e) in results.items()}},
        ))

        # finalize, then (re)compute completeness over the complete event set
        self._finalize(seq, dims)
        final_events = self.store.events(self.run_id)
        dims.completeness = evaluator._complete(final_events)
        # policy_blocked = a tool policy actually rejected a request this run
        if self.policy_manifest is not None:
            dims.policy_blocked = any(
                e.event_type == "policy.decided" and e.payload.get("decision") == "deny"
                for e in final_events
            )
        self.dims = dims
        # rewrite the finalized event to carry the corrected final dimensions
        self._patch_finalized_payload(seq, dims)

        # persist findings now that all dimensions are final
        self.store.add_finding(self.run_id, 0, "utility",
                               dims.task_success and "pass" or "fail",
                               _join_results("utility", results))
        self.store.add_finding(self.run_id, 0, "security",
                               dims.attack_succeeded and "pass" or "fail",
                               _join_results("security", results))
        return dims

    def _select_trace(self, scenario: Scenario) -> list[Decision]:
        v = self.config.variant
        # The decision trace only says what the agent *tries*. Policy enforcement
        # is server-side (ToolService), so the same attack trace is used whether
        # or not a policy is active — the policy is what blocks the forbidden
        # send, producing blocked-vs-vulnerable comparison.
        if v == "benign" and scenario.benign_trace:
            return _trace_decisions(scenario.benign_trace)
        if v == "attack" and scenario.attack_trace:
            return _trace_decisions(scenario.attack_trace)
        return []

    def _finalize(self, seq, dims: RunResultDimensions) -> None:
        self.store.append_event(EventRecord(
            run_id=self.run_id, event_id=uuid.uuid4().hex, sequence=seq(),
            timestamp=_now(), actor="supervisor", event_type="run.finalized",
            payload={"status": "completed", "dimensions": dims.summary()},
        ))
        self.status = RunStatus.COMPLETED
        self.store.update_run_status(self.run_id, "completed", _now())

    def _patch_finalized_payload(self, seq, dims: RunResultDimensions) -> None:
        self.store.patch_event_payload(
            self.run_id, "run.finalized",
            {"status": "completed", "dimensions": dims.summary()},
        )

    # ------------------------------------------------------------------ #
    def snapshot_dims(self) -> RunResultDimensions | None:
        return self.dims


class RunError(Exception):
    pass


async def _run_guard(adapter, context: Any, scenario: Scenario):
    from ..adapters.protocol import run_adapter

    return await asyncio.wait_for(
        run_adapter(adapter, context),
        timeout=scenario.manifest.limits.timeout_seconds,
    )


def _default_adapter():
    # lazily import to keep cli/app light until needed
    from ..adapters.protocol import ReferenceAdapter

    return ReferenceAdapter()


def _make_tool_fn(tools: ToolService, name: str):
    async def _fn(args: dict[str, Any]) -> Any:
        tool_call_id = uuid.uuid4().hex
        result = tools.execute(name, args, tool_call_id=tool_call_id,
                               parent_event_id=None)
        if result.error:
            raise BrokerError(result.error)
        return result.value
    return _fn


def _join_results(prefix: str, results: dict[str, tuple[Outcome, str]]) -> str:
    parts = [f"{k[len(prefix)+1:]}:{o.value}" for k, (o, _) in results.items() if k.startswith(prefix + ":")]
    return ",".join(parts) if parts else "no_predicates"


class _Context:
    """Minimal RunContext implementation for the reference adapter."""

    def __init__(self, task, tools, model, budget, cancelled) -> None:
        self.task = task
        self.tools = tools
        self.model = model
        self.budget = budget
        self.cancelled = cancelled

    def result(self, final_output: str, finish_reason: str = "stop",
               metadata: dict[str, Any] | None = None) -> AgentResult:
        return AgentResult(final_output=final_output, finish_reason=finish_reason,
                           adapter_metadata=metadata or {})