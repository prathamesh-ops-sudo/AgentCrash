# ADR-0001: Synthetic tool boundary

- **Status:** Accepted
- **Date:** 2026-09-09

## Context
AgentCrash tests prompt-injection in agents. If it wired real tools (real mail,
HTTP egress, shell), a run could contact real external systems and testing
would be neither safe nor reproducible.

## Decision
The tool plane exposes only enumerated synthetic operations (`documents.read`,
`notes.write`, `mail.send`) on an in-memory `WorldState`. Outbound mail writes to
a local outbox sink; nothing ever reaches a real external recipient. The tool
service is the single producer of authoritative side-effect events
(`world.changed`), giving the evaluator a trusted record.

## Consequences
- Runs are safe, offline, and deterministic.
- "Attack succeeded" means a synthetic canary appeared in a local sink — never
  real credential theft. Editorial rules forbid labeling one as the other.
- `ToolService` is not an HTTP proxy and does not execute shell commands.

## Alternatives
- Generic tool passthrough (rejected: unsafe, non-reproducible).
- Real tooling behind an allowlist (rejected: introduces external side effects).

## Revisit trigger
If we adopt arbitrary user-provided tools, revisit isolation (see ADR-0002).