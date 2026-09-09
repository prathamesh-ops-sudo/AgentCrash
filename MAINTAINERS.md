# Maintainers

This file states current maintainership, decision authority, review rules, and
open roles for AgentCrash. It complements [CONTRIBUTING.md](CONTRIBUTING.md)
(contributor workflow), [SECURITY.md](SECURITY.md) (disclosure), and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Roles

- **Owner — Prathamesh Dabir.** The project owner is the final authority on
  repository structure, scope, and direction, and the decision maker for
  **security** and **release** matters. Nothing that touches a trust boundary,
  sandbox profile, broker, or the release pipeline is merged without their
  sign-off.

| Role | Holder | Authority |
|------|--------|-----------|
| Owner / security & release decision maker | Prathamesh Dabir | Final say on scope, security posture, and what ships. |

## Two-person review for sandbox / broker / release

Changes to the sandbox isolation profiles, the model broker (credential
handling, endpoint allowlist, budget enforcement), the tool service/policy
enforcement, and the release pipeline require **two-person review**: the change
must be reviewed and approved by a maintainer other than the author, in
addition to the owner's security/release decision. This is the control behind
the security invariant "do not change schemas without migration + contract
tests" and "do not publish unsupported install commands".

Scope that triggers two-person review (non-exhaustive):

- `src/agentcrash/sandbox/**` — isolation profiles and launcher.
- `src/agentcrash/broker/**` — model access, budgets, credential handling.
- `src/agentcrash/tools/policy.py` + policy schema — enforcement path.
- `src/agentcrash/adapters/protocol.py` + schema changes — adapter contract.
- The release/CI pipeline and any README install placeholder marked
  `VERIFIED_PACKAGE`.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for the
security invariants and completion requirements a two-person review enforces.

## Weekly triage and issue labels

Maintainers triage incoming issues weekly:

- Label `installation` — setup/onboarding problems.
- Label `security` — trust boundaries, isolation, secrets → owner + second review.
- Label `adapters` — user-agent integration.
- Label `scenarios` — synthetic fixtures and evaluator fixtures.
- Label `evaluation` — result semantics, metrics.
- Label `documentation` — docs, recipes, README.
- Label `good first issue` — bounded file set with expected behavior.

Each PR should be linked to a labeled issue so weekly triage can route and
close out work. Security reports follow [SECURITY.md](SECURITY.md) and are
triaged within 10 working days.

## Open roles

- **Backup release maintainer (open).** The owner is the single
  security/release decision maker today. A backup release maintainer is needed
  so a release or security fix is never blocked by one person's availability.
  Responsibilities: own release mechanics, verify the release on a clean
  machine, and hold release keys/handles in a way that does not depend on the
  owner alone.

## Code of conduct enforcement contact

Code of conduct enforcement contact is currently a **placeholder** — see
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Until an enforcement contact is
appointed, escalate conduct reports to the owner; do not leave reports unread.