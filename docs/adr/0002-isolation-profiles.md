# ADR-0002: Isolation profiles for the worker

- **Status:** Accepted (profile contract); live container driver is scaffolding
- **Date:** 2026-09-09

## Context
Per the security model, a run may encounter malicious prompt content and
untrusted worker/adapter code. The host filesystem, provider credentials, local
services, and other runs must be protected.

## Decision
Adapters run only in declared isolation profiles. The v0.1 default profile
(`agentcrash-worker-default`) requires: non-root user, read-only rootfs, all
capabilities dropped, no privileged mode, no host PID or network namespace,
bounded writable tmpfs, memory/process/CPU limits, and an enabled seccomp
policy. No Docker socket is ever mounted. A `ContainerProfile` is validated by
`validate_profile()` in `sandbox/profile.py`; violating profiles raise.

The deterministic demo/CI path runs an explicitly-labeled *uncontained*
execution profile for replay only; it is never labeled as contained.

## Consequences
- `validate_profile` refuses any profile that weakens these invariants
  (`privileged`, root user, host network/PID, writable rootfs, runtime socket).
- `sandbox/tests` assert these blockers.
- A Compose network flag alone is not treated as a guarantee; the launcher must
  validate the container properties.

## Alternatives
- Ship each adapter fully isolated by default (deferred: heavier, not needed
  for the offline replay).
- Trust the user's host entirely (rejected: this is a security tool).

## Revisit trigger
macOS/Windows VM-backed runtimes, or adopting community adapters, require
re-validating resource and network behavior per platform.