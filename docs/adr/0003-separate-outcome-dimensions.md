# ADR-0003: Separate utility and security outcome dimensions

- **Status:** Accepted
- **Date:** 2026-09-09

## Context
A single "agent is safe" score hides the distinction that defines the product:
did the legitimate task still succeed while an attack was blocked? Collapsing
task completion and attacker success into one number makes an incomplete run, a
blocked-everything defense, and a genuinely good defense look identical.

## Decision
Every run reports five separated dimensions: `task_success` (utility),
`attack_attempted`, `attack_succeeded` (attacker goal in authoritative state),
`policy_blocked`, and `completeness`. They are never merged into a security
pass. The `RunResultDimensions` dataclass in `schemas/models.py` is the
single source. A cancelled or partial run is `completeness=False` and can never
be a clean pass.

## Consequences
- The viewer reports and the CLI table render these independently.
- "Blocked everything" (task fails, attack blocked) is easy to spot versus a
  working fix (task succeeds, attack blocked) — a stated requirement.
- JUnit export maps a failure/incomplete to a failure/error, never a pass.

## Alternatives
- A composite risk score (rejected: hides the utility/security trade-off and
  invites misleading claims).

## Revisit trigger
If a future feature needs a rolled-up score for a specific scrub, it must stay
sibling to these dimensions, not replace them.