# AgentCrash — integrate your agent

This directory shows how a developer wires their own tool-using agent into
AgentCrash through the adapter interface. The reference adapter lives in
`src/agentcrash/adapters/protocol.py`; this example is a minimal working clone
you can copy into your project and adapt.

## What you get

The adapter receives a `RunContext` with:

- `task` — the synthetic user task.
- `tools` — a dict of `name -> async callable` for the **synthetic** tool
  client. Policy is enforced server-side by the tool service.
- `model` — a scoped model broker that holds the provider credential.
- `budget` — `max_tool_calls`.
- `cancelled` — an `asyncio.Event`.

It returns an `AgentResult` (final output + metadata). Task success and the
security verdict are computed independently by the evaluator — never by the
adapter.

## Example adapter

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

## Requirement: the integration boundary

Only the agent path wired through AgentCrash tools and model access is under
test. You must:

1. Replace real tools with the provided synthetic tool client (`context.tools`).
2. Route model calls through `context.model` (the broker), not your own key.
3. Remove inherited credentials and network access from the agent's process.

If a framework insists on unmanaged tools or direct endpoints, mark its
integration unsupported until a recipe enforces that boundary. The adapter must
report its tool and model capability requirements **before** execution.

## Wiring the synthetic tools

AgentCrash tools are simple `async` functions taking a dict of arguments. A
framework adapter usually needs a small mapping layer:

```python
def wire_tools(context: RunContext) -> dict:
    return {
        name: _adapt(context.tools[name]) for name in context.tools
    }

async def _adapt(fn):
    # adapt to whatever signature your framework's tool executor expects
    return lambda args: fn(args)
```

## Validate + run

See the CLI docs for the exact commands. The gist:

```bash
agentcrash adapters validate my-agent
agentcrash run --adapter my-agent --scenario invoice-confidential-note --variant benign
agentcrash run --adapter my-agent --scenario invoice-confidential-note --variants attack
agentcrash compare BASELINE_GROUP_ID DEFENDED_GROUP_ID
```

## Tested contracts

The adapter interface is frozen by contract tests in `tests/contract/`. Any
change to `RunContext` or `AgentResult` requires updating those tests first.

## Reference adaptation

The reference adapter (`src/agentcrash/adapters/protocol.py`) is a minimal
tool-calling loop that is deliberately simple so its behavior is auditable and
deterministic under the scripted broker. Read it as the canonical example.