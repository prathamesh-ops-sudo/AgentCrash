# Tool policy format

Policies control which **synthetic** tool operations an agent may perform.
They are enforced by the tool service **before any effect occurs**. The default
stance is explicit deny: unknown constructs fail configuration validation
rather than being silently ignored, and a tool that is not allowlisted is
denied.

Policies are data only (safe YAML, `extra="forbid"` on the manifest) and live
anywhere you can pass a path — for example `examples/policies/`.

## Example: `examples/policies/invoice-summary-only.yaml`

```yaml
schema_version: 1
id: invoice-summary-only
description: >
  Permit reading the invoice and writing the internal summary note while
  rejecting sends to any recipient outside the internal finance mailbox.
rules:
  documents.read:
    allowed_document_ids:
      - invoice-001
  notes.write:
    allowed_note_ids:
      - invoice_summary
  mail.send:
    allowed_recipients:
      - finance@example.invalid
default: deny
```

## Contract

- `schema_version` — must equal the supported version (`1`).
- `id` — policy identifier (used in run metadata and policy-diff digests).
- `description` — human note.
- `rules` — map of tool name to a `ToolRule`.
- `default` — `allow` or `deny` (default `deny`).

A `ToolRule` may carry any of:

| Field | Applies to tool | Semantics |
|-------|-----------------|-----------|
| `allowed_document_ids` | `documents.read` | Only these documents may be read. |
| `allowed_note_ids` | `notes.write` | Only these notes may be written. |
| `allowed_recipients` | `mail.send` | Only these recipients may be mailed. |
| `allowed_fields` | (extensible) | Allowlisted argument fields. |
| `extra` | (extensible) | Reserved for future rule kinds. |

A field set to `null`/omitted means **no constraint** for that axis; a
non-null list is an exact allowlist. If the rule's constraint list is set and
the requested value is not in it, the request is denied with a reason string.

## Allowlist + default-deny semantics

- If **no policy** is configured, the tool service allows the enumerated
  synthetic operations (`documents.read`, `notes.write`, `mail.send`).
- If a policy **is** configured and `default: deny` (the default), any tool
  not present in `rules` is denied: `tool <name> not allowlisted (default deny)`.
- A tool that **is** in `rules` is checked against its per-axis allowlists; a
  requested id/recipient outside the list is denied (e.g. `document 'x' not allowed`).
- There is no LLM judge, heuristic, or natural-language model in the
  enforcement path — enforcement is exact allowlist and argument validation.

## Argument normalization

Normalization happens inside the enforcer (`src/agentcrash/tools/policy.py`)
so that enforcement and evaluation see identical canonical values. The policy
decision carries the normalized arguments, and `policy_blocked` is decided from
the tool service's `policy.decided` events — never from the worker's account of
what it believes it was allowed to do.

## Enforcement is in the tool service

The enforcer (`PolicyEnforcer.decide(tool_name, arguments) -> Decision`) is
called server-side, before any effect. This is the same trust boundary as the
security model's tool plane: the agent process cannot bypass the check by
requesting an effect directly, because there is no tool path outside the
service (see [ADR-0001](../adr/0001-synthetic-tool-boundary.md)).

## Configuration

Apply a policy to a run with:

```bash
uv run agentcrash run invoice-confidential-note \
    --variant attack --policy examples/policies/invoice-summary-only.yaml
```

If the policy file is invalid (bad YAML, unknown fields, wrong schema version)
the run is rejected before execution. `agentcrash init` writes a config that
points at this example policy by default so a fresh workspace starts with the
default-deny stance in mind.