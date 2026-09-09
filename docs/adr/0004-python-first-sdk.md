# ADR-0004: Python-first SDK with a separate CLI and viewer

- **Status:** Accepted
- **Date:** 2026-09-09

## Context
The product must be useful through the CLI alone, and the browser viewer must
not be a second implementation of security decisions. Every entry path (CLI,
HTML report, JUnit, local API) must agree on results.

## Decision
Python (`src/agentcrash/`) is the single implementation of the runner,
evaluation, policies, events, and reports. All exporters (`json`, `html`,
`junit`, JSONL) are generated from the same `RunResultDimensions` + event
stream. The React viewer talks only to the local FastAPI `/v1` endpoints; it
performs no security decision of its own. The runner lives under `core/` and
the UI artifacts are bundled into the wheel so release users never run Node.

## Consequences
- One source of truth for results; CLI and browser always agree.
- The offline replay and deterministic CI need no model key, Docker, or Node.
- Adapters import the Python SDK; `RunContext` and `AgentResult` are frozen by
  contract tests in `tests/contract/`.

## Alternatives
- A JS-native evaluator (rejected: duplicate logic and divergence risk).

## Revisit trigger
If the viewer needs to make an offline-only decision the backend cannot, that
capability returns to the backend first.