# Exit codes

The CLI is the single stable surface for automation. Exit codes are part of the
API contract and are relied on by CI.

| Code | Meaning |
|------|---------|
| 0 | Complete results meeting declared thresholds; or a clean run. |
| 1 | Observed test failure (a predicate failed, or an attack variant leaked / became incomplete). |
| 2 | Invalid configuration or unsupported capabilities; unknown run id. |
| 3 | Infrastructure or provider failure. If a suite has both findings and an infrastructure failure, we return 3 and preserve per-trial findings in the report. |
| 4 | Budget exhaustion (future: reserved). |
| 130 | User interruption. |

## Rules

- `--fail-on` may configure test predicates, but it must never turn incomplete
  evidence into a successful CI result.
- An incomplete or cancelled run is never exit 0.
- Machine output uses `--json` and writes only structured JSON to stdout; human
  diagnostics go to stderr, so parsing stdout in a pipeline is safe.
- Avoid interactive prompts in CI.