# Contributing to AgentCrash

Thanks for helping people crash-test their agents. This file gets you from a
fresh clone to a passing deterministic test in ten minutes.

## Ten-minute setup

```bash
git clone <repository-url>
cd agentcrash
uv sync --all-extras
uv run agentcrash demo          # opens the offline recorded demo
uv run pytest tests/unit tests/contract
uv run ruff check .
uv run mypy src
```

Python 3.12 is the baseline. The frontend lives under `web/` (React + TS +
Vite); you only need Node to build the viewer, not to use the product.

## Issue labels

- `installation` — setup/onboarding problems
- `security` — trust boundaries, isolation, secrets
- `adapters` — integration with a user agent
- `scenarios` — synthetic fixtures and evaluator fixtures
- `evaluation` — result semantics, metrics
- `documentation` — docs, recipes, README
- `good first issue` — bounded file set with expected behavior

Please route bug reports, integration requests, scenario submissions, and
security reports to the appropriate template.

## Review process

Changes land through a pull request. A maintainer (or a second review for
sandbox/broker/release changes) reviews:

- focused scope with a user-visible behavior described in the linked issue,
- reproducible test instructions,
- updated docs for any user-visible flag/output/support change,
- no material generated code merged that the author has not understood.

AI assistance is welcome; the contributor remains responsible for correctness
and licensing.

## Contributing a scenario

Scenario contributors must include:

- a synthetic fixture (no production credentials, no uncontrolled external services),
- a benign control variant,
- an exact attacker objective,
- deterministic evaluator tests,
- source attribution and license,
- reset behavior (a rerun starts from the identical fixture),
- resource limits,
- a redacted sample report.

Maintainers review whether the case teaches or tests a **distinct** threat
boundary. See `docs/concepts/scenarios.md` for the full authoring guide.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Enforcement contact is named
there.