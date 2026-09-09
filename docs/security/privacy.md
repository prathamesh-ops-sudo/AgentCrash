# Privacy

AgentCrash runs adversarial content and potentially user-written adapter code,
so privacy behavior is part of the threat model. This page states where data
lives, what leaves the machine, and what redaction does and does not do.

> **Scope honesty.** These are defaults and design intentions for v0.1, not
> guarantees that hold under a compromised host, a malicious report reader, or
> adversarial local storage. See the [security model](model.md) for the tested
> trust boundary.

## Local storage under the OS user data directory

Run data — the SQLite store (runs, events, findings, trial groups), run-scoped
blobs, and generated reports — is written under the **OS user data directory**
by default. You can redirect it per-command with `--data-dir D`. Nothing is
stored in shared or world-writable locations. The demo report (default
`demo.html`) is also written under the same user data directory unless you pass
`--out`.

## Telemetry is off by default

AgentCrash sends no usage telemetry, crash reports, or analytics. The optional
`webview` extra lists `sentry-sdk` only as a **placeholder** for future opt-in
crash telemetry; it is not active at runtime in v0.1. Default behavior is fully
local. If a future version adds telemetry it must be opt-in, never silently on.

## Offline demo sends no model traffic

`agentcrash demo` is a recorded replay: it uses the `scripted` model backend,
makes **no API key, no model calls, and no Docker** calls. No prompt is
transmitted anywhere. Its output report is labeled `"mode": "recorded"` so it
cannot be mistaken for a live measurement.

## Live runs transmit prompts to the configured provider

A **live** `agentcrash run --model <provider>` sends the synthetic prompt to the
configured model provider through the broker (which requires the `provider`
extra and a configured endpoint). Only allowlisted HTTPS endpoints are used;
redirects and destination addresses are checked, and the provider credential is
inserted by the broker, never exposed to the worker. If you do not want prompt
content to leave the machine, do not configure a live provider — the offline
`scripted` backend needs none.

## Explicit redaction and preview for exports

`agentcrash export RUN_ID` does **not** exfiltrate anything by itself — it
writes a JSONL bundle to a path you choose. It supports explicit, repeatable
secrets to redact:

```bash
uv run agentcrash export <RUN_ID> --preview --secret model_key --secret prompt
uv run agentcrash export <RUN_ID> --out bundle.jsonl --secret model_key
```

`--preview` prints what will be redacted **without writing anything**, so you
can review before sharing. Redaction is explicit, not assumed: declare what you
want scrubbed. There is no background upload and no implicit share.

## Purge is best-effort

`agentcrash purge RUN_ID` removes a run's events/findings and marks the run row
`purged`. This is **not** secure erasure: it does not guarantee removal from
SSD remnants, OS-level caches, or backups. If you need strong deletion, purge
is only the first step and you must also handle copies outside AgentCrash's
control. See [CLI reference](../reference/cli.md#purge).

## Limits of local disk protection

Local disk protection has limits. Under a compromised host kernel or a local
administrator there is no guarantee of confidentiality for on-disk evidence,
config, or the provider endpoint policy. The v0.1 security model explicitly
does **not** claim to withstand those (see [model.md](model.md)). Store the
data directory on media/at permissions you trust, and treat exports as files
you are responsible for after they leave AgentCrash.