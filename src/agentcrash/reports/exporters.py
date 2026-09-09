"""Report exporters: JSON, standalone HTML, JUnit — generated from the same
result object so CLI and browser views always agree.

HTML is standalone (no external scripts/fonts/images/analytics), escapes all
payloads, and drives the offline viewer with CSS variables for accessibility.
"""
from __future__ import annotations

import html
import json
from typing import Any

from ..evidence.store import EventStore, export_jsonl
from ..schemas.models import EventRecord, RunResultDimensions


def _dim(dims: RunResultDimensions) -> dict[str, Any]:
    return dims.summary()


def report_json(store: EventStore, run_id: str, dims: RunResultDimensions,
                predicates: dict[str, Any] | None = None) -> str:
    events = [ev.__dict__ for ev in store.events(run_id)]
    doc = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "completed",
        "dimensions": _dim(dims),
        "predicates": predicates or {},
        "events": events,
    }
    return json.dumps(doc, indent=2, default=str)


def report_junit(store: EventStore, run_id: str, dims: RunResultDimensions,
                 predicates: dict[str, Any] | None = None) -> str:
    """JUnit-style XML for CI. Non-passing predicates become failures; an
    incomplete run is reported as an error, never a success."""
    assertions = []
    for k, (outcome, evidence) in (predicates or {}).items():
        name = k.replace(":", ".")
        if outcome.value == "pass":
            assertions.append(
                f'    <testcase classname="agentcrash.{run_id}" name="{_esc(name)}">'
                f'<system-out>{_esc(evidence)}</system-out></testcase>'
            )
        else:
            assertions.append(
                f'    <testcase classname="agentcrash.{run_id}" name="{_esc(name)}">'
                f'<failure type="assertion">{_esc(evidence)}</failure></testcase>'
            )
    if not dims.completeness:
        assertions.append(
            f'    <testcase classname="agentcrash.{run_id}" name="completeness">'
            f'<error type="incomplete">run lacks required evidence; never a pass</error></testcase>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuite name="agentcrash.{_esc(run_id)}" tests="{len(assertions)}">\n'
        + "\n".join(assertions) + "\n"
        "</testsuite>\n"
    )


def report_html(store: EventStore, run_id: str, dims: RunResultDimensions,
                predicates: dict[str, Any] | None = None,
                events: list[EventRecord] | None = None,
                mode: str = "recorded") -> str:
    """Standalone, escaped, self-contained HTML report."""
    events = events if events is not None else store.events(run_id)
    dim = _dim(dims)

    def _label(v):
        return {
            True: "Yes", False: "No", None: "n/a",
        }.get(v, str(v))

    rows = "".join(
        f"<tr><td>{_esc(ev.event_type)}</td><td>{_esc(ev.actor)}</td>"
        f"<td>{_esc(ev.timestamp)}</td>"
        f"<td><details><summary>payload</summary><pre>{_esc(json.dumps(ev.payload, default=str))}</pre></details></td></tr>"
        for ev in events
    )

    pred_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{_esc(o.value)}</td><td>{_esc(e)}</td></tr>"
        for k, (o, e) in (predicates or {}).items()
    )

    color = {"pass": "var(--pass, #2e7d32)", "fail": "var(--fail, #c62828)",
             "not_evaluated": "var(--muted-foreground, #777)"}

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>AgentCrash report — {_esc(run_id)}</title>
<style>
:root {{ --fg:#111; --muted:#555; --border:#ddd; --card:#fff; --bg:#f7f7f7; --pass:#2e7d32; --fail:#c62828; --amber:#b26a00; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg:#eee; --muted:#aaa; --border:#333; --card:#1c1c1c; --bg:#121212; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:system-ui,Segoe UI,sans-serif; color:var(--fg); background:var(--bg); }}
.wrap {{ max-width:960px; margin:auto; padding:24px; }}
h1 {{ font-size:20px; }} h2 {{ font-size:16px; margin-top:28px; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:16px; margin:8px 0; }}
.dims {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }}
.dim {{ border-left:4px solid var(--border); padding:8px 12px; background:var(--card); border-radius:4px; }}
.dim b {{ display:block; font-size:12px; text-transform:uppercase; color:var(--muted); }}
.dim span {{ font-size:15px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
td,th {{ border:1px solid var(--border); padding:6px 8px; text-align:left; vertical-align:top; }}
pre {{ white-space:pre-wrap; word-break:break-word; margin:0; max-height:200px; overflow:auto; }}
details>pre {{ margin-top:4px; }}
.mode {{ display:inline-block; font-size:11px; text-transform:uppercase; letter-spacing:.5px; color:var(--muted); border:1px solid var(--border); border-radius:4px; padding:2px 8px; }}
</style>
</head>
<body><div class="wrap">
<div class="card">
  <h1>AgentCrash report</h1>
  <div>Run <code>{_esc(run_id)}</code> <span class="mode">mode: {_esc(mode)}</span></div>
</div>
<div class="card"><h2>Outcome dimensions</h2><div class="dims">
  <div class="dim" style="border-color:{color.get('pass','')}"><b>Task success</b><span>{_label(dim['task_success'])}</span></div>
  <div class="dim" style="border-color:{color.get('amber','')}"><b>Attack attempted</b><span>{_label(dim['attack_attempted'])}</span></div>
  <div class="dim" style="border-color:{color.get('fail','')}"><b>Attack succeeded</b><span>{_label(dim['attack_succeeded'])}</span></div>
  <div class="dim" style="border-color:{color.get('amber','')}"><b>Policy blocked</b><span>{_label(dim['policy_blocked'])}</span></div>
  <div class="dim" style="border-color:{color.get('muted','')}"><b>Completeness</b><span>{_label(dim['completeness'])}</span></div>
</div></div>
<div class="card"><h2>Evaluator predicates</h2><table><tr><th>Predicate</th><th>Outcome</th><th>Evidence</th></tr>{pred_rows}</table></div>
<div class="card"><h2>Event timeline</h2><table><tr><th>Type</th><th>Actor</th><th>Time</th><th>Payload</th></tr>{rows}</table></div>
</div></body></html>"""


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def build_result_dict(store: EventStore, run_id: str, dims: RunResultDimensions,
                      predicates: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "dimensions": _dim(dims),
        "predicates": predicates or {},
        "events": [ev.__dict__ for ev in store.events(run_id)],
        "jsonl": export_jsonl(store, run_id),
    }