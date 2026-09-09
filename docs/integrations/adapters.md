# Writing an AgentCrash adapter

An adapter wires a developer's own tool-using agent into AgentCrash so it can
be crash-tested against the synthetic world. Adapters are **not** proxies to
production tools; they replace real tools with the provided synthetic tool
client and route model calls through the broker. This page expands on the
minimal example in `examples/adapter_integration.md` and adds capability
reporting and contract-test guidance.

## The protocol

`src/agentcrash/adapters/protocol.py` defines three types:

- `RunContext` — what the adapter receives:
  - `task` — the synthetic user task.
  - `tools` — `dict[str, ToolFn]` of `name -> async callable` for the synthetic
    tool client. Policy is enforced server-side by the tool service.
  - `model` — a scoped model broker that holds the provider credential.
  - `budget` — `max_tool_calls`.
  - `cancelled` — an `asyncio.Event`.
  - `result(final_output, finish_reason="stop", metadata=None) -> AgentResult`.
- `AgentAdapter` — the interface your class implements:
  `async def run(self, context: RunContext) -> AgentResult`.
- `AgentResult` — `final_output`, `finish_reason`, `adapter_metadata`,
  `tool_calls_made`. **Task success and the security verdict are not computed
  here**; the independent evaluator computes them from tool-service events and
  world state.

`run_adapter()` wraps `adapter.run(context)` with a friendly
timeout/cancellation wrapper and requires `run` to be a coroutine function
(`asyncio`); a non-async `run` raises `AdapterError`.

## Minimal adapter

```python
# my_agent.py
from agentcrash.adapters.protocol import RunContext, AgentResult


class MyAgentAdapter:
    """Replace production tools with the synthetic ones, route model calls
    through the broker, and drop inherited credentials/network access."""

    async def run(self, context: RunContext) -> AgentResult:
        agent = build_my_agent(tools=context.tools, model=context.model)
        output = await agent.run(context.task, budget=context.budget,
                                 cancel=context.cancelled)
        return context.result(final_output=output)
```

## The integration boundary (mandatory)

Only the agent path wired **through** AgentCrash tools and model access is
under test. For a valid integration you must:

1. Replace real tools with `context.tools` (the synthetic client) — never call
   production services from the agent.
2. Route model calls through `context.model` (the broker), **not** your own key.
3. Remove inherited credentials and network access from the agent's process.

If a framework insists on unmanaged tools or direct endpoints, mark that
integration **unsupported** until a recipe enforces the boundary. The model
broker authoritatively validates provider requests, enforces budget/endpoint
policy, and inserts the credential; the worker never touches the host
credential store (see [security model](../security/model.md)).

## Capability reporting

A well-written adapter reports its requirements **before** it executes, so a
run can be rejected early instead of failing halfway:

- **Tools required** — which of `documents.read`, `notes.write`, `mail.send`
  (or scenario-declared tools) the agent must have. If the scenario does not
  declare one of them, the adapter should say so rather than silently working
  around the gap.
- **Model access** — whether it needs live model calls (broker) or can run on
  the `scripted` backend.
- **Boundary guarantees** — confirmation that real tools and host credentials
  are not reachable, and that cancellation (`context.cancelled`) is honored.

Capability information should be emitted as `adapter_metadata` and, where a
framework cannot satisfy the declared boundary, the integration should be
flagged unsupported before a run starts. This keeps a scenario from "passing"
only because the adapter quietly bypassed the tools it claimed to use.

Policy is still enforced regardless: the tool service decides
`policy_blocked`; the adapter's own report of capability does not bypass that
check.

## Contract tests

The repository's `tests/contract/` suite validates the adapter protocol and
the schemas. Before you send a new adapter, ensure:

- **Protocol shape** — `run` is async, takes a `RunContext`, returns an
  `AgentResult` (or raises `AdapterError`).
- **No verdict leakage** — the adapter does not write `task_success` /
  `attack_succeeded`; those come from the evaluator.
- **Trust boundary** — no tool-call path exists outside `context.tools`, and no
  model-call path outside `context.model`.
- **Determinism under scripted traces** — the adapter behaves identically on
  repeated runs of the same benign/attack/blocked trace (the CI
  demo/deterministic path runs a recorded replay with no model).

Run the contract and unit suites locally before opening a PR:

```bash
uv run pytest tests/unit tests/contract
uv run ruff check .
uv run mypy src
```

Changes to the adapter protocol must not land without the accompanying contract
test updates.

## Validate + run

```bash
uv run agentcrash scenarios --validate
uv run agentcrash run --scenario invoice-confidential-note --variant benign --adapter my-agent
uv run agentcrash run --scenario invoice-confidential-note --variant attack --adapter my-agent
uv run agentcrash compare <BASELINE_RUN_ID> <DEFENDED_RUN_ID>
```

Start with the benign variant to confirm the legitimate task completes, then
verify the attack variant produces the expected dimensions. See the
[first run](../getting-started/first-run.md) guide for the full journey.