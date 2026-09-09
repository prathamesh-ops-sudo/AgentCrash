## Summary

<!-- What behavior changes and why. Link the issue (e.g. Closes #123). -->

## Scope / files changed

<!-- Bounded file set. Do not bundle unrelated changes. -->

## Test evidence

<!-- How to reproduce and what you observed. Attach run output / exit codes. -->

- [ ] `uv run pytest tests/unit tests/contract tests/integration tests/e2e -q` passes locally
- [ ] `uv run ruff check src tests` passes
- [ ] `uv run mypy src` passes
- [ ] User-visible changes are documented (README/docs) if any

## Security notes

<!-- If this touches a trust boundary (sandbox, broker, evaluator, packs, exports,
  local API, release), describe the verification and any limitation. -->

## AI assistance

<!-- Disclose material generated code you have not fully understood. -->

## Checklist

- [ ] No host mounts, arbitrary egress, secrets in logs, or fabricated benchmark output added.
- [ ] No schema change without migration and contract tests.
- [ ] I verified the integrated behavior (ran it), not just that "tests passed".