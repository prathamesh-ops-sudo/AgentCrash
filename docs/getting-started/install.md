# Installing AgentCrash

AgentCrash is a Python 3.12 command-line tool. This page covers prerequisites,
installing the published wheel or installing from source, and verifying the
install with the offline demo.

> **Alpha caveat.** v0.1 is a developer tool. The deterministic demo/CI path is
> fully offline; live sandboxed execution of a user model requires a container
> runtime and is not claimed to protect a compromised host kernel.

## Prerequisites

- **Python 3.12** (the declared baseline; `requires-python = ">=3.12"`).
- **uv** (recommended) or **pipx** to manage the virtual environment. Either is
  fine; only one is needed.

If you are building the bundled web viewer (`svg`/`serve`, the React app under
`web/`) you also need Node, but it is **not** required to use the product.

## Install the published wheel

Once a release exists, the pinned, verifiable install is:

```bash
uvx --from agentcrash==0.1.2 agentcrash demo
```

or install it as a tool and verify:

```bash
uv tool install agentcrash==0.1.2
agentcrash --version
agentcrash doctor --mode demo
```

`agentcrash doctor --mode demo` checks the Python baseline and the scenario
pack root and is the fastest sanity check that the install is intact.

### Clean-machine note (unverified placeholders)

Until a release has actually been produced and run on a fresh machine,
`VERIFIED_PACKAGE` is a placeholder. The exact `agentcrash==X.Y.Z` and URL
values written in documentation are **unverified** and may not resolve
anywhere until the first real release. Install commands in this document that
use concrete version pins are validated only when a corresponding section of
`CHANGELOG.md` and the release pipeline say so. Do not copy a `VERIFIED_PACKAGE`
placeholder into automation or publish it as tested before it is proven on a
clean machine.

## Install from source

For development or when you want the branch on disk:

```bash
git clone <repository-url>
cd agentcrash
uv sync --all-extras
```

`--all-extras` installs the optional dependency groups (`server`, `provider`,
`test`, `dev`) on top of the core runtime. Development extras add tooling:

- `server` — FastAPI/uvicorn/sse-starlette, needed by `agentcrash serve`.
- `provider` — httpx, needed for live model calls through the broker.
- `test` — pytest/pytest-asyncio/hypothesis/ruff/mypy, for running the suite.

From a checkout you can run everything through uv without activating anything:

```bash
uv run agentcrash demo
uv run pytest tests/unit tests/contract
uv run ruff check .
uv run mypy src
```

## Verify with the offline demo

The flagship demo needs **no API key, no model calls, and no Docker**. It runs
a labeled *recorded* replay of the `invoice-confidential-note` scenario through
the same pipeline as a live run and writes a standalone HTML report:

```bash
uv run agentcrash demo
```

The report is saved (default `demo.html` in the user data directory) and its
output is clearly identified as `"mode": "recorded"`.

## Next steps

- Walk through the [first run](first-run.md) journey: demo, doctor, init, a
  benign then attack run, a report, a policy comparison, and an export.
- See the full [CLI reference](../reference/cli.md) for every command and flag.
- Read the [security model](../security/model.md) before running anything that
  executes untrusted content in a sandbox.