# Evidence and results

AgentCrash treats a run as a sequence of timestamped events written to an
authoritative store, plus a final set of result dimensions computed by an
independent evaluator. This page explains the dimensions, the event model, the
storage backends, the run-mode labels, and the invariant that **missing
evidence is never a pass**.

## Result dimensions

Five boolean dimensions are kept **separately** and never collapsed into one
score (see [ADR-0003](../adr/0003-separate-outcome-dimensions.md)).

| Dimension | Question it answers | Author of truth |
|-----------|--------------------|-----------------|
| `task_success` | Did the legitimate task assertion hold? | Evaluator (utility predicate) |
| `attack_attempted` | Was the forbidden request observed? | Evaluator (security predicate) |
| `attack_succeeded` | Did the simulated attacker goal occur in the synthetic world? | Evaluator (security predicate) |
| `policy_blocked` | Did the tool policy reject the request? | Tool service `policy.decided` events |
| `completeness` | Does the run have all required evidence? | Supervisor/run lifecycle |

Key rules:

- The **adapter never computes** utility or security verdicts. `AgentResult`
  is finish output + metadata; the evaluator decides from tool-service events
  and world state.
- `policy_blocked` is answered by the tool service's enforcement decision, not
  by the worker's self-report.
- `completeness` gates everything: an incomplete or cancelled run is never
  `task_success`/secure and never exits `0`.

## Event types

Runs are captured as an ordered, typed event stream. The authoritative set
(`src/agentcrash/evidence/store.py`, `EVENT_TYPES`):

| Event type | Actor | Meaning |
|------------|-------|---------|
| `run.started` | supervisor | Run begun; authoritative first event. |
| `model.requested` / `model.completed` | broker | Model call lifecycle. |
| `tool.requested` | worker | A tool action was requested. |
| `tool.rejected` | tool service | The request was rejected before effect. |
| `policy.decided` | tool service | Policy verdict for a request. |
| `tool.executed` | tool service | An allowed tool produced an effect. |
| `world.changed` | tool service | The synthetic world was mutated. |
| `agent.completed` | worker | The agent finished with final output. |
| `evaluator.completed` | evaluator | Predicate results recorded. |
| `run.cancelled` | supervisor | Interrupted before completion. |
| `run.failed` | supervisor | A run-level failure occurred. |
| `run.finalized` | supervisor | Run sealed; carries the final `dimensions`. |

The evaluator and supervisor actors are authoritative. **Worker-emitted events
are untrusted** and can never establish an authoritative side effect; only
tool-service events and world state can.

## Storage: SQLite and JSONL

- **SQLite** is the canonical store, holding runs, events, findings, and trial
  groups. Run data lives under the OS user data directory by default
  (override with `--data-dir`). Large payloads are kept in a run-scoped blob
  directory addressed by digest, so diagnostics do not need raw content.
- **JSONL** is the portable append-oriented export format, used by
  `agentcrash report --format jsonl` and `agentcrash export`.

## Replay vs. live vs. counterfactual labeling

Runs are labeled by how the evidence was produced, and consumers must respect
the label:

- **Replay (recorded).** The offline demo (`agentcrash demo`) drives a scripted
  decision trace through the same pipeline as a live run and writes a report
  labeled `"mode": "recorded"`. It makes **no model calls** and is a
  deterministic demonstration, not a live measurement of an agent.
- **Live.** A real run (`agentcrash run`) executes an adapter against the
  synthetic world and records events as they occur. Live work against a model
  requires a container runtime; without containment you are not testing the
  same trust boundary the model.md describes.
- **Counterfactual.** A report can be produced from stored evidence after the
  fact. Rebuilding a report from events is a view of an already-recorded run,
  not new evidence.

Do not present a recorded replay or a rebuilt report as a fresh live result.

## Why missing evidence is never a pass

Every security decision depends on authoritative evidence: a predicate that
"sees" the attacker goal in the world, a tool-service decision that blocked it,
a sealed `run.finalized`. If any required evidence is absent — the run was
cancelled, timed out, the evaluator never completed, or the world was not
mutated — the run is `completeness=False` and cannot be called a security
success. `--fail-on` may configure which predicate gates exit `1`, but nothing
can turn incomplete evidence into a `0`.

See [exit codes](../reference/exit-codes.md) for the numeric contract, and the
[security model](../security/model.md) for why the evaluator is structured to
be independent of worker explanation.