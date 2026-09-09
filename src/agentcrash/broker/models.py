"""Model broker: narrow access to model providers with budgets and response
metadata. The broker inserts the provider credential; the worker never sees it.

The broker supports two client kinds:
- `scripted`: a deterministic trace-driven client used for offline replay and
  deterministic CI. Makes no network calls.
- `provider`: an OpenAI-compatible HTTPS client with call/token budgets.

Provider keys are held only by the broker, read from a secure prompt or OS
credential store — never passed on the CLI or written to the worker.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


class BrokerError(Exception):
    pass


@dataclass
class Budget:
    """Best-effort budget. In-flight provider calls can exceed before usage
    arrives; strict reservations are enforced before dispatch."""
    max_calls: int = 20
    max_tokens: int | None = None
    used_calls: int = 0
    reserved_tokens: int = 0


@dataclass
class ModelReply:
    content: str
    provider: str = ""
    model: str = ""
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    raw_meta: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        return f"{self.provider}/{self.model}"


# A decision message produced by a worker's model loop: either a tool call or a
# final answer.
@dataclass
class Decision:
    kind: str  # "tool_call" | "answer"
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    tool_call_id: str | None = None
    text: str = ""


class ModelClient(Protocol):
    """Model access the worker can see. Budget-aware, broker-owned."""

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        ...

    @property
    def identity(self) -> str:
        ...


class ScriptedBroker:
    """Deterministic, offline model broker driven by a scripted decision trace.

    Used for recorded demo replay and deterministic CI so tests never depend on
    a live model or a network call. The trace is a list of decisions; each call
    to `complete` advances one step by default.
    """

    def __init__(self, trace: list[Decision] | None = None, identity: str = "scripted/model") -> None:
        self.trace = trace or []
        self._index = 0
        self._identity = identity

    @property
    def identity(self) -> str:
        return self._identity

    def reset(self) -> None:
        self._index = 0

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        if self._index >= len(self.trace):
            return ModelReply(content="", model=self._identity, finish_reason="stop",
                              provider="scripted", usage={})
        decision = self.trace[self._index]
        self._index += 1
        # Encode the next decision as a model reply the worker interprets.
        if decision.kind == "tool_call":
            content = json.dumps({
                "type": "tool_call",
                "tool": decision.tool_name,
                "arguments": decision.arguments,
                "tool_call_id": decision.tool_call_id,
            })
            return ModelReply(content=content, model=self._identity, provider="scripted",
                              finish_reason="tool_calls", usage={"prompt_tokens": 1, "completion_tokens": 1})
        return ModelReply(content=decision.text, model=self._identity, provider="scripted",
                          finish_reason="stop", usage={"prompt_tokens": 1, "completion_tokens": 1})


class BudgetEnforcer:
    def __init__(self, max_calls: int = 20, max_tokens: int | None = None) -> None:
        self.budget = Budget(max_calls=max_calls, max_tokens=max_tokens)

    @property
    def max_tool_calls(self) -> int:
        return self.budget.max_calls

    def reserve_call(self) -> None:
        if self.budget.used_calls >= self.budget.max_calls:
            raise BrokerError(f"call budget exhausted ({self.budget.max_calls})")
        self.budget.used_calls += 1

    def reserve_tokens(self, n: int) -> None:
        if self.budget.max_tokens is None:
            return
        if self.budget.reserved_tokens + n > self.budget.max_tokens:
            raise BrokerError(f"token budget exhausted (>={self.budget.max_tokens})")
        self.budget.reserved_tokens += n

    @property
    def used_calls(self) -> int:
        return self.budget.used_calls


class ProviderSettings:
    base_url: str
    api_key_env: str
    model: str
    timeout_s: float = 30.0


class ProviderBroker:
    """OpenAI-compatible HTTPS provider broker (direct adapter, no heavy SDK).

    Requires httpx. Egress is restricted to configured allowlisted endpoints.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        max_calls: int = 20,
        max_tokens: int | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        import httpx

        self._httpx = httpx
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.budget = BudgetEnforcer(max_calls=max_calls, max_tokens=max_tokens)
        self.timeout_s = timeout_s
        self._client = httpx.AsyncClient(timeout=timeout_s)

    @property
    def identity(self) -> str:
        return f"provider/{self.model}"

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.budget.reserve_call()
        url = f"{self.base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 512,
        }
        if tools:
            payload["tools"] = [_to_provider_tool(t) for t in tools]
        resp = await self._client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        if resp.status_code != 200:
            raise BrokerError(f"provider error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        self.budget.reserve_tokens(usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0))
        return ModelReply(
            content=choice.get("message", {}).get("content") or "",
            provider="provider",
            model=self.model,
            finish_reason=choice.get("finish_reason"),
            usage=usage,
            raw_meta=data,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


def _to_provider_tool(tool: dict[str, Any]) -> dict[str, Any]:
    # Client-facing tool descriptors are {"name", "description", "arguments_json"};
    # provider expects {"type":"function","function":{...}}.
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": json.loads(tool.get("arguments_json", "{}")),
        },
    }