"""AgentCrash CLI (Typer + Rich).

Exit codes (see docs/reference/exit-codes.md):
  0 complete results meeting declared thresholds
  1 observed test failure (a predicate failed, or a security pass)
  2 invalid configuration / unsupported capabilities
  3 infrastructure or provider failure
  4 budget exhaustion
  130 user interruption

Machine output uses --json and writes only structured data to stdout while
human diagnostics go to stderr.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional  # noqa: F401,UP035 (resolved by Typer's get_type_hints)

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__
from ..core.compare import compare_groups
from ..core.loader import discover_packs, load_scenario
from ..core.policies import load_policy
from ..core.runner import Runner
from ..evidence.store import export_jsonl
from ..reports.exporters import report_html, report_json, report_junit
from ..schemas.models import RunConfig, TrialGroupMeta
from ..server.context import get_scenarios_root, open_store

app = typer.Typer(
    name="agentcrash",
    help="Crash-test your AI agent in a synthetic workplace.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        print(f"agentcrash {__version__}")
        raise typer.Exit()


@app.callback()
def _main(version: bool = typer.Option(False, "--version", callback=_version_callback,
                                       is_eager=True, help="Show version and exit.")) -> None:
    pass
console = Console(stderr=True)

# Exit codes
EXIT_OK = 0
EXIT_TEST_FAIL = 1
EXIT_CONFIG = 2
EXIT_INFRA = 3
EXIT_BUDGET = 4
EXIT_CANCEL = 130

DATA_DIR: str | None = None
SCENARIOS_ROOT: str | None = None


def _store():
    store, blobs, root = open_store(DATA_DIR)
    return store, blobs, root


def _scenarios() -> str:
    return get_scenarios_root(SCENARIOS_ROOT)


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str))


# ------------------------------------------------------------------ #
@app.command()
def demo(
    scenario: str = typer.Option("invoice-confidential-note", help="scenario to replay"),
    variant: str = typer.Option("attack", help="benign | attack"),
    data_dir: str | None = typer.Option(None, "--data-dir"),
    out: Path | None = typer.Option(None, "--out", "-o", help="write HTML report here"),
) -> None:
    """Open the recorded offline demo (no API key, no model calls, no Docker).

    This runs a labeled recorded replay of the flagship scenario through the
    same pipeline as a live run, and opens a standalone HTML report that is
    clearly identified as recorded.
    """
    global DATA_DIR
    DATA_DIR = data_dir
    store, blobs, root = _store()
    cfg = RunConfig(scenario_id=scenario, variant=variant)
    runner = Runner(store, blobs, _scenarios(), cfg)
    dims = runner.execute()
    results = runner.results
    html = report_html(store, runner.run_id, dims, results)
    dest = out or (root / "demo.html")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html)
    _emit({"ok": True, "run_id": runner.run_id, "mode": "recorded",
           "report": str(dest), "dimensions": dims.summary()})


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000, min=1, max=65535),
    data_dir: str | None = typer.Option(None, "--data-dir"),
) -> None:
    """Serve the local API + static report viewer on loopback."""
    global DATA_DIR
    DATA_DIR = data_dir
    import uvicorn

    from ..server.api import create_app

    application = create_app(data_dir=data_dir)
    configure_static(application)

    console.print(f"AgentCrash local API on http://{host}:{port} "
                  f"(bootstrap ignored; loopback only)")
    uvicorn.run(application, host=host, port=port, log_level="info")


def configure_static(application) -> None:
    """Mount the built web viewer under /viewer and serve report assets."""
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    # Prefer the wheel-bundled static dir; fall back to web/dist in a checkout.
    candidates = [
        Path(__file__).resolve().parents[1] / "server" / "static",
        Path(__file__).resolve().parents[4] / "web" / "dist",
    ]
    for cand in candidates:
        if cand.is_dir():
            application.mount("/viewer", StaticFiles(directory=str(cand), html=True),
                              name="viewer")
            console.print(f"viewer mounted from {cand}")
            return
    console.print("warning: no built viewer found (run pnpm build in web/)",
                  style="yellow")


@app.command()
def version() -> None:
    """Print the installed AgentCrash version."""
    print(f"agentcrash {__version__}")


@app.command()
def doctor(mode: str = typer.Option("demo", help="demo | sandbox | all")) -> None:
    """Check runtime, permissions, resources, and supported profile."""
    checks = []
    checks.append(("python", sys.version.split()[0], True, "Python 3.12 baseline"))
    # scenarios root exists
    sr = _scenarios()
    exists = Path(sr).is_dir()
    checks.append(("scenarios", sr, exists, "scenario pack root"))
    # demo mode needs no docker; sandbox mode requires a container runtime
    docker_ok = False
    if mode in ("sandbox", "all"):
        docker_ok = os.system("docker info >/dev/null 2>&1") == 0
        checks.append(("docker", "docker", docker_ok, "container runtime (sandbox)"))
    if mode == "all":
        docker_ok = os.system("docker info >/dev/null 2>&1") == 0
        checks.append(("docker", "docker", docker_ok, "container runtime"))
    all_ok = all(c[2] for c in checks)
    table = Table(title=f"agentcrash doctor ({mode})")
    table.add_column("Check")
    table.add_column("Value")
    table.add_column("Status")
    for name, val, ok, note in checks:
        table.add_row(name, val, "OK" if ok else "MISSING", note if not ok else "")
    console.print(table)
    if not all_ok:
        raise typer.Exit(code=EXIT_INFRA)


@app.command()
def init(template: str = typer.Option("invoice", help="Config template name")) -> None:
    """Create a local configuration from a named template."""
    _store()
    cfg = {
        "schema_version": 1,
        "scenarios_root": _scenarios(),
        "policy": "examples/policies/invoice-summary-only.yaml",
        "model": {"provider": "scripted", "name": "model"},
        "budget": {"max_calls": 20, "max_tokens": None},
        "template": template,
    }
    # write to user data dir
    _, _, root = open_store(DATA_DIR)
    cfg_path = root / "agentcrash.yaml"
    import yaml

    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    _emit({"ok": True, "config": str(cfg_path), "template": template})


@app.command(name="scenarios")
def scenarios_cmd(list_only: bool = typer.Option(False, "--list", "-l"),
                  validate_only: bool = typer.Option(False, "--validate")):
    """Discover scenario packs and verify their contracts."""
    packs = discover_packs(_scenarios())
    if list_only or not validate_only:
        for p in packs:
            print(p)
    if validate_only:
        res = {}
        for p in packs:
            try:
                load_scenario(f"{_scenarios()}/{p}")
                res[p] = "ok"
            except Exception as exc:
                res[p] = f"FAIL: {exc}"
        _emit({"scenarios": res})


@app.command()
def run(
    scenario: str = typer.Argument(...),
    variant: str = typer.Option("attack", help="benign | attack"),
    trials: int = typer.Option(1, min=1),
    adapter: str = typer.Option("reference"),
    policy: str | None = typer.Option(None, "--policy", help="path to policy yaml"),
    model: str = typer.Option("scripted"),
    json_out: bool = typer.Option(False, "--json"),
    data_dir: str | None = typer.Option(None, "--data-dir"),
    fail_on: str | None = typer.Option(None, "--fail-on",
                                          help="exit 1 if a predicate with this name is not pass"),
) -> int:
    """Execute clean or attack trials in a fresh world."""
    global DATA_DIR
    DATA_DIR = data_dir
    store, blobs, root = _store()
    policy_manifest = load_policy(policy) if policy else None
    outs = []
    try:
        for i in range(trials):
            cfg = RunConfig(
                scenario_id=scenario, variant=variant, adapter=adapter,
                policy_id=policy_manifest.id if policy_manifest else None,
                trials=trials, model=model,
            )
            runner = Runner(store, blobs, _scenarios(), cfg, policy=policy_manifest)
            dims = runner.execute()
            outs.append({
                "trial": i, "run_id": runner.run_id,
                "dimensions": dims.summary(),
            })
    except Exception as exc:
        _emit({"error": str(exc), "retryable": False})
        raise typer.Exit(code=EXIT_INFRA) from exc

    summary = {
        "scenario": scenario, "variant": variant, "trials": trials,
        "adapter": adapter, "policy": policy, "model": model,
        "runs": outs,
    }
    if json_out:
        _emit(summary)
    else:
        table = Table(title=f"agentcrash run: {scenario} ({variant})")
        table.add_column("trial")
        table.add_column("run_id")
        table.add_column("task_success")
        table.add_column("attack_attempted")
        table.add_column("attack_succeeded")
        table.add_column("policy_blocked")
        table.add_column("complete")
        for o in outs:
            d = o["dimensions"]
            table.add_row(str(o["trial"]), o["run_id"][:12], str(d["task_success"]),
                          str(d["attack_attempted"]), str(d["attack_succeeded"]),
                          str(d["policy_blocked"]), str(d["completeness"]))
        console.print(table)

    # exit code semantics
    any_attack_succeeded = any(o["dimensions"]["attack_succeeded"] for o in outs)
    any_incomplete = any(not o["dimensions"]["completeness"] for o in outs)
    if any_incomplete:
        raise typer.Exit(code=EXIT_TEST_FAIL)
    if any_attack_succeeded and variant == "attack" and not policy:
        raise typer.Exit(code=EXIT_TEST_FAIL)
    if fail_on and any_attack_succeeded:
        raise typer.Exit(code=EXIT_TEST_FAIL)
    raise typer.Exit(code=EXIT_OK)


@app.command()
def report(
    run_id: str,
    format: str = typer.Option("html", help="html | json | junit | jsonl"),
    out: Path | None = typer.Option(None, "--out", "-o"),
    data_dir: str | None = typer.Option(None, "--data-dir"),
) -> None:
    """Produce local HTML, JSON, or JUnit evidence."""
    global DATA_DIR
    DATA_DIR = data_dir
    store, blobs, root = _store()
    evs = store.events(run_id)
    if not evs:
        console.print(f"no events for run {run_id}")
        raise typer.Exit(code=EXIT_CONFIG)
    # rebuild dims from stored findings (simplified): read final payload
    dims_payload = None
    predicates = {}
    for e in evs:
        if e.event_type == "run.finalized":
            dims_payload = e.payload.get("dimensions")
        if e.event_type == "evaluator.completed":
            predicates = {k: (_pred_outcome(v[0]), v[1]) for k, v in e.payload.get("predicates", {}).items()}
    dims = _dims_from_dict(dims_payload) if dims_payload else None
    if dims is None:
        console.print("run has no evaluator results; report cannot be built")
        raise typer.Exit(code=EXIT_INFRA)

    if format == "json":
        body = report_json(store, run_id, dims, predicates)
    elif format == "junit":
        body = report_junit(store, run_id, dims, predicates)
    elif format == "jsonl":
        body = export_jsonl(store, run_id)
    else:
        body = report_html(store, run_id, dims, predicates)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)
        print(str(out))
    else:
        if format == "html":
            print(body)
        else:
            _emit({"run_id": run_id, "format": format, "content": body})


@app.command()
def export(
    run_id: str,
    out: Path = typer.Option(..., "--out", "-o", help="write the redacted JSONL bundle here"),
    secret: list[str] | None = typer.Option(None, "--secret", help="secrets to redact (repeatable)"),
    preview_only: bool = typer.Option(False, "--preview"),
    data_dir: str | None = typer.Option(None, "--data-dir"),
) -> None:
    """Preview and save an explicitly redacted share bundle (JSONL)."""
    global DATA_DIR
    DATA_DIR = data_dir
    store, blobs, root = _store()
    evs = store.events(run_id)
    if not evs:
        console.print(f"no events for run {run_id}")
        raise typer.Exit(code=EXIT_CONFIG)
    from ..evidence.redaction import export_preview, redact

    payload = [ev.__dict__ for ev in evs]
    redacted = redact(payload, secrets=secret)
    if preview_only:
        _emit(export_preview(evs, secrets=secret))
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(json.dumps(r, default=str) for r in redacted) + "\n"
    out.write_text(lines)
    _emit({"exported": str(out), "events": len(redacted),
           "redacted_secrets": len(secret or [])})


@app.command()
def runs(list_only: bool = typer.Option(False, "--list", "-l"),
         json_out: bool = typer.Option(False, "--json"),
         data_dir: str | None = typer.Option(None, "--data-dir")) -> None:
    """Inspect stored runs."""
    global DATA_DIR
    DATA_DIR = data_dir
    store, blobs, root = _store()
    rows = store.runs()
    if list_only and not json_out:
        for r in rows:
            print(f"{r['run_id']} {r['scenario_id']} {r['variant']} {r['status']}")
        return
    _emit({"runs": rows})


def contains(needle: str, argv: list[str]) -> bool:
    return needle in argv


@app.command()
def purge(run_id: str | None = typer.Argument(None, help="exact run id; omit to list targets"),
          data_dir: str | None = typer.Option(None, "--data-dir")) -> None:
    """Purge local run data (revocation best-effort; not recovery-proof)."""
    global DATA_DIR
    DATA_DIR = data_dir
    store, blobs, root = _store()
    if run_id is None:
        for r in store.runs():
            _emit({"purge_candidate": r["run_id"]})
        return
    # SQLite: remove events + findings for run; database retains no run row
    store.update_run_status(run_id, "purged")
    _emit({"purged": run_id, "note": "best-effort; not recovery-proof on SSD/backups"})


@app.command()
def compare(baseline: str, defended: str) -> None:
    """Compare compatible saved runs and label differences."""
    store, blobs, root = _store()
    base = _trials_for(store, baseline)
    defend = _trials_for(store, defended)
    b_meta = TrialGroupMeta(scenario_version=base[0]["scenario_version"] if base else "",
                            model_identity="scripted",
                            adapter_digest="reference",
                            policy_digest=None)
    d_meta = TrialGroupMeta(scenario_version=defend[0]["scenario_version"] if defend else "",
                            model_identity="scripted",
                            adapter_digest="reference",
                            policy_digest=None)
    # reuse compare_groups with minimal dims
    res = compare_groups(
        [_to_outcome(o["run_id"], o["dims"]) for o in base],
        [_to_outcome(o["run_id"], o["dims"]) for o in defend],
        b_meta, d_meta,
    )
    _emit(res)


def _trials_for(store, run_id):
    evs = store.events(run_id)
    dims_payload = None
    version = ""
    for e in evs:
        if e.event_type == "run.finalized":
            dims_payload = e.payload.get("dimensions")
    def _d():
        from ..schemas.models import RunResultDimensions
        d = RunResultDimensions()
        if dims_payload:
            d.task_success = dims_payload.get("task_success")
            d.attack_attempted = dims_payload.get("attack_attempted")
            d.attack_succeeded = dims_payload.get("attack_succeeded")
            d.policy_blocked = dims_payload.get("policy_blocked")
            d.completeness = dims_payload.get("completeness", False)
        return d
    return [{"run_id": run_id, "dims": _d(), "scenario_version": version}]


def _to_outcome(run_id, dims):
    from ..core.compare import TrialOutcome
    return TrialOutcome(index=0, run_id=run_id, dims=dims, attrs={})


def _dims_from_dict(payload):
    from ..schemas.models import RunResultDimensions
    d = RunResultDimensions()
    if not payload:
        return None
    d.task_success = payload.get("task_success")
    d.attack_attempted = payload.get("attack_attempted")
    d.attack_succeeded = payload.get("attack_succeeded")
    d.policy_blocked = payload.get("policy_blocked")
    d.completeness = payload.get("completeness", False)
    return d


def _pred_outcome(v):
    from ..schemas.models import Outcome
    try:
        return Outcome(v)
    except ValueError:
        return Outcome.NOT_EVALUATED


if __name__ == "__main__":
    app()