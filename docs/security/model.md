# Security model

AgentCrash is itself a security-sensitive application: it runs adversarial
content and potentially user-written adapter code. This page states the threat
model and the mandatory controls that are validated by tests.

> The MVP threat model permits malicious prompt content and untrusted worker
> code **within the declared container boundary**. It does not claim to
> withstand a compromised host kernel or a local administrator.

## Assets to protect

- Host filesystem
- Provider credentials
- Local services
- Other runs (cross-run isolation)
- Evidence integrity
- Release pipeline
- Report recipients

## What is untrusted

Scenario files, model responses, adapter code, imported reports, and community
pull requests.

## Trust boundaries

### Tool plane
Only enumerated synthetic operations (`documents.read`, `notes.write`,
`mail.send`). It is **not** an HTTP forward proxy and does **not** execute shell
commands. Outbound mail writes to a local outbox sink; a "remote upload" writes
to a local sink. Observing that sink proves the defined simulated outcome, not
real external contact.

### Evaluator
The evaluator consumes authoritative tool-service events and world state, never
worker explanation. Guest-emitted events are marked untrusted and can never
establish an authoritative side effect. Key expectations and verdicts stay
outside the guest's readable filesystem.

### Model broker
Validates provider requests, enforces budget and endpoint policy, inserts the
provider credential, returns the response. The worker cannot access the host
credential store. Only configured HTTPS endpoints allowed; redirects and
destination addresses are checked.

## Required controls (validated by tests)

| Threat | Required control | Verified by |
|--------|------------------|-------------|
| Host file access | No host home mounts; fixed fixture mount; resolved path confinement | loader + sandbox tests |
| Provider key exposure | Broker-only credential storage, scrubbed environment | sandbox tests |
| Unrestricted egress | Worker network isolation; broker allowlist | profile validation |
| Tool side-effect spoofing | Evaluator trusts tool-service events only | runner/evaluator tests |
| Pack code execution | Data-only packs; no install hooks | loader tests |
| Resource exhaustion | Time, memory, CPU, process, disk, call limits | profile + budget |
| Report injection | Escaped text; no remote assets; standalone HTML | exporter tests |
| Local API misuse | Loopback bind, Host/Origin/environment checks, CSRF | API contract tests |
| Supply chain | Locked deps, reviewed releases, provenance | CI |
| Evidence leakage | Local storage, explicit export, redaction preview | redaction tests |

## Container profile invariants

Tested in `tests/sandbox/`: non-root user, read-only rootfs, dropped
capabilities, no privileged mode, no host PID/network namespace, bounded
writable tmpfs, resource limits, seccomp enabled. Docker socket is never
mounted inside the worker. `validate_profile()` refuses any violation.

## Release blockers

Before a public beta, all of these must hold (see AGENTS.md):
1. No fixture can execute code in the host loader.
2. No export runs embedded script.
3. No guest sees a provider key.
4. No unsupported environment is labeled contained.
5. No partial run receives a pass.