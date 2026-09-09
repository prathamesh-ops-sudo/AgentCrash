# CLI reference

AgentCrash's CLI is the single stable surface for automation. Run entries are
Typer commands; `--json` writes only structured JSON to stdout while human
diagnostics go to stderr, so piping stdout in a pipeline is safe. This page
documents every command, its flags, and exit behavior, matching the commands
in the installed binary. It does not list flags that do not exist.

Global behavior:

- `agentcrash` with no arguments prints help.
- Every data-writing command accepts `--data-dir D` to override the run store.
- Exit codes: see [exit-codes.md](exit-codes.md).

## `demo`

Replay the recorded offline demo.

```
agentcrash demo [--scenario SCENARIO] [--variant benign|attack]
                [--data-dir D] [--out PATH | -o PATH]
```

- `--scenario` — scenario to replay (default `invoice-confidential-note`).
- `--variant` — `benign` or `attack` (default `attack`).
- `--out` / `-o` — write the HTML report here (default `demo.html` in the user
  data dir).

Runs the scripted trace through the same pipeline as a live run with **no API
key, no model calls, no Docker**, and writes a standalone HTML report labeled
`"mode": "recorded"`. Exit `0` on success.

## `doctor`

Check the runtime environment.

```
agentcrash doctor [--mode demo|sandbox|all]
```

- `demo` (default) — Python 3.12 baseline and scenario pack root.
- `sandbox` — additionally checks for a container runtime (`docker info`);
  reports it missing rather than pretending live containment exists.
- `all` — all checks.

Exit `3` if any check fails, else `0`.

## `init`

Create a local configuration from a named template.

```
agentcrash init [--template NAME]
```

Writes `agentcrash.yaml` into the user data directory (default template
`invoice`) pointing at the scenario root, the example policy
(`examples/policies/invoice-summary-only.yaml`), a scripted model, and a budget
(`max_calls: 20`). Nothing is executed. Returns the config path. Exit `0`.

## `scenarios`

Discover and validate scenario packs.

```
agentcrash scenarios [--list | -l] [--validate]
```

- `--list` / `-l` — list discovered pack ids.
- `--validate` — attempt to load every pack; emit `{"scenarios": {"<id>": "ok"|"FAIL: ..."}}`.

Exit `0` (validation reports failures in the JSON, per-pack). A malformed or
unsafe pack fails validation loudly before any run.

## `run`

Execute clean or attack trials in a fresh world.

```
agentcrash run SCENARIO [--variant benign|attack] [--trials N]
                       [--adapter NAME] [--policy PATH] [--model MODEL]
                       [--json] [--data-dir D] [--fail-on PREDICATE]
```

- `SCENARIO` — scenario id (positional, required).
- `--variant` — `benign` or `attack` (default `attack`).
- `--trials N` — number of trials (default 1, min 1).
- `--adapter NAME` — adapter to run (default `reference`).
- `--policy PATH` — path to a policy YAML (no policy = allow all enumerated
  operations).
- `--model MODEL` — model backend (default `scripted`).
- `--json` — emit machine output on stdout.
- `--fail-on PREDICATE` — exit `1` if the named predicate is not pass.

Prints a table (or JSON) of the five dimensions per trial. Exit codes:

- `0` — complete results meeting thresholds.
- `1` — any trial incomplete, or (attack variant without policy) any attack
  succeeded, or `--fail-on` fired.
- `3` — infrastructure/provider failure during execution.
- `2` — configuration/validation error.

**Import rule:** `--fail-on` must never turn incomplete evidence into exit `0`.

## `report`

Produce local HTML, JSON, JUnit, or JSONL evidence for a stored run.

```
agentcrash report RUN_ID [--format html|json|junit|jsonl]
                        [--out PATH | -o PATH] [--data-dir D]
```

- `RUN_ID` — the stored run id (positional, required).
- `--format` — `html` (default), `json`, `junit`, or `jsonl`.
- `--out` / `-o` — write the file (default: prints HTML to stdout, or emits
  `{run_id, format, content}` JSON for machine formats).

Exit `2` if the run id is unknown or has no events; `3` if the run has no
evaluator results to build a report from; else `0`. Reports are rebuilt from
stored evidence.

## `export`

Preview and write an explicitly redacted share bundle (JSONL).

```
agentcrash export RUN_ID --out PATH
                [--secret VALUE ...] [--preview] [--data-dir D]
```

- `RUN_ID` — stored run id (positional, required).
- `--out` / `-o` — destination JSONL file (required).
- `--secret VALUE` — repeatable; a secret to redact from the bundle.
- `--preview` — print the redaction preview and exit without writing.

Exit `2` if the run id is unknown/no events; else `0`.

## `runs`

Inspect stored runs.

```
agentcrash runs [--list | -l] [--json] [--data-dir D]
```

- `--list` / `-l` — one `run_id scenario_id variant status` line per run.
- `--json` — emit the full runs payload.

Exit `0`.

## `purge`

Purge local run data (best-effort; not recovery-proof).

```
agentcrash purge [RUN_ID] [--data-dir D]
```

- With `RUN_ID` — remove the run's events/findings and mark the run row
  `purged`. Emits `{"purged": RUN_ID, "note": "best-effort; not recovery-proof on SSD/backups"}`.
- Without `RUN_ID` — emit `{"purge_candidate": run_id}` for each stored run
  (dry-run listing) without deleting.

Purging is **not** secure erasure; it does not guarantee undoing backups or
SSD/OS-level remnants. Exit `0`.

## `compare`

Compare two compatible saved runs and label differences.

```
agentcrash compare BASELINE_RUN_ID DEFENDED_RUN_ID
```

Emits a JSON comparison of the two trial outcomes' dimensions. Exit `0`.

## `serve`

Serve the local API + static report viewer on loopback.

```
agentcrash serve [--host HOST] [--port PORT] [--data-dir D]
```

- `--host` — bind host (default `127.0.0.1`).
- `--port` — TCP port (default `8000`, range 1–65535).

Requires the `server` extra (`uv sync --all-extras`). Exposes FastAPI `/v1`
endpoints (`/v1/capabilities`, `/v1/scenarios`, `/v1/runs`, `/v1/runs/{id}`,
`/v1/runs/{id}/cancel` [stub], `/v1/runs/{id}/events`, `/v1/runs/{id}/exports`,
`/healthz`) and the React viewer under `/viewer`. Loopback bind with Host/Origin
enforcement; it is not a network service. Requires `web/dist` (or the
wheel-bundled static) to exist for the viewer.

## `version`

```
agentcrash version
```

Print the installed version. Exit `0`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Complete results meeting declared thresholds. |
| `1` | Observed test failure (a predicate failed, or an attack leaked/incomplete). |
| `2` | Invalid configuration / unsupported capability / unknown run id. |
| `3` | Infrastructure or provider failure (infra wins over findings when both occur; per-trial findings are preserved in the report). |
| `4` | Budget exhaustion (reserved for future). |
| `130` | User interruption. |

Machine consumers should treat only `0` as clean, and never map incomplete
evidence to success.