# Changelog

All notable changes to AgentCrash are recorded here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-09-12

Release-pipeline fix. No runtime behavior changes.

### Fixed
- **The `Release` workflow failed on every tag.** The publish step relied on
  PyPI *trusted publishing*, which was never configured for the repository, so
  the OIDC token exchange was refused with
  `invalid-publisher: valid token, but no corresponding publisher`. Releases
  were landing on PyPI only when published by hand. The workflow now
  authenticates with the repository secret `PYPI_API_TOKEN`.
- Documented `PACKAGE_VERSION` drift: the schema package constant still read
  `0.1.0`; it now tracks the package version.

## [0.1.1] - 2026-09-11

Release-readiness fixes. The 0.1.0 wheel only worked on the maintainer's
machine; this release makes a clean install work everywhere.

### Fixed
- **Scenarios were unresolvable off the maintainer's machine.** Discovery fell
  back to a hardcoded absolute Windows path, and the packaged lookup resolved one
  directory too high, so `agentcrash run` failed with
  `scenarios/<id>: not a directory` on any other host and in CI.
- **`uv sync` failed on a fresh clone.** The wheel build force-included a
  generated, gitignored directory (`server/static`) that does not exist until the
  web viewer is built, so contributors and CI could not install the project.
- **Corrected package metadata.** The PyPI project URLs pointed at a
  non-existent repository and a placeholder documentation site.

### Changed
- The web viewer is bundled with hatchling `artifacts`, so builds succeed when
  the viewer has not been built and include it when it has.
- CI now runs on the default branch (`master`); it previously targeted `main`
  and had never executed.

## [0.1.0] - 2026-09-09

Initial developer release of the open-source agent security test harness.

### Added
- **Scenario engine**: data-only scenario packs (safe YAML manifest + fixtures),
  a deterministic scripted model broker, a reference tool-calling adapter, and
  separated utility/security outcome dimensions.
- **5 first-party scenarios** (`scenarios/`) with benign + attack variants and
  policy-blocked comparison: invoice-confidential-note, support-tenant-boundary,
  document-write-redirection, tool-response-instruction, persistent-note-poisoning.
- **Synthetic tool service**: `documents.read`, `notes.write`, `mail.send` on an
  in-memory world with idempotency keys (retries cannot duplicate a send) and an
  authoritative event store (SQLite) with JSONL export.
- **Tool policies**: allowlisted tool names, argument validation, allowed
  recipients/documents/notes, default-deny. Enforcement happens in the tool
  service, not an LLM judge.
- **Evaluator predicates**: `world_field_equals`, `world_field_changed`,
  `canary_in_outbox`, `read_attempted`.
- **CLI** (`agentcrash`): `demo`, `doctor`, `init`, `scenarios`, `run`,
  `report` (html/json/junit/jsonl), `compare`, `runs`, `purge`, `serve`,
  `version`; documented exit codes.
- **Local API + React viewer**: FastAPI `/v1` endpoints on loopback with
  Host/Origin enforcement; static viewer bundled into the wheel.
- **Sandbox profile**: validated invariant profile (non-root, read-only rootfs,
  dropped capabilities, no host network/PID, bounded tmpfs).
- **Tests**: contract, unit (tool service), sandbox (invariant blockers),
  integration (scenario bench), e2e (CLI exit codes + wheel install).
- **CI/Release** workflows (`.github/workflows/`), license/docs/ADRs.

### Security
- Provider keys are broker-only; no secrets printed to stdout.
- Exports are escaped, standalone HTML; incomplete runs are never passes.
- Scenario packs are data-only; no code executes from a pack on the host.

### Notes
- v0.1 deterministic path runs a labeled *uncontained* replay for demo/CI. Live
  sandboxed execution requires a container runtime and a built worker image.
- Install commands in the README use unverified placeholders until a release is
  published and proven on a clean machine.