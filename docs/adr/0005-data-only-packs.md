# ADR-0005: Data-only scenario packs

- **Status:** Accepted
- **Date:** 2026-09-09

## Context
Community scenario submissions are a growth engine, but a pack that can execute
code on the host loader is an RCE channel. The threat model treats scenario
files, model responses, adapter code, and imported reports as untrusted.

## Decision
Scenario packs are data only: a `scenario.yaml` manifest plus fixture files
(world JSON, task text, injected content, scripted decision traces). The safe
YAML loader (`core/loader.py`) uses `yaml.SafeLoader`, refuses python/constructor
tags, and denies fixture paths that escape the pack directory. There are no
install hooks and no executable entries. Manifest schema is `extra="forbid"` so
unknown fields are rejected rather than silently executed.

## Consequences
- A malformed or hostile pack fails validation loudly, before any run.
- Packs have attribution/license fields; adaptation of public incidents keeps
  original attribution.
- No code runs from a pack on the host loader.

## Alternatives
- Allow user scripts in packs (rejected: RCE and reproducibility hazard).
- Accept a generic data blob (rejected: no typed limits or licenses).

## Revisit trigger
Adding an adaptive-attack research profile later must keep packs data-only and
keep the evaluator inaccessible to the generator and target agent.