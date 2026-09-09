import React, { useEffect, useState } from "react";

const BASE = "";

function label(v) {
  if (v === true) return "Yes";
  if (v === false) return "No";
  if (v === null || v === undefined) return "n/a";
  return String(v);
}

export default function App() {
  const [scenarios, setScenarios] = useState([]);
  const [status, setStatus] = useState("loading");
  const [runResult, setRunResult] = useState(null);
  const [runError, setRunError] = useState(null);
  const [selected, setSelected] = useState("");
  const [variant, setVariant] = useState("attack");
  const [report, setReport] = useState(null);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    fetch(`${BASE}/v1/scenarios`)
      .then((r) => r.json())
      .then((d) => {
        setScenarios(d.scenarios || []);
        setSelected((d.scenarios || [])[0] || "");
        setStatus("ready");
      })
      .catch(() => setStatus("offline"));
  }, []);

  async function run() {
    setRunError(null);
    setRunResult(null);
    setReport(null);
    setEvents([]);
    try {
      const res = await fetch(`${BASE}/v1/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_id: selected, variant }),
      });
      const data = await res.json();
      if (!res.ok) {
        setRunError(data.detail || "run failed");
        return;
      }
      setRunResult(data);
      const ev = await (await fetch(`${BASE}/v1/runs/${data.run_id}/events`)).json();
      setEvents(ev.events || []);
      const exp = await fetch(`${BASE}/v1/runs/${data.run_id}/exports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format: "json" }),
      });
      setReport(await exp.json());
    } catch (e) {
      setRunError(e.message);
    }
  }

  if (status !== "ready") {
    return (
      <div className="card muted">
        {status === "loading" ? "Loading scenarios…" : "Local API not reachable. Start with: agentcrash serve"}
      </div>
    );
  }

  const dims = runResult?.dimensions || null;

  return (
    <div className="wrap">
      <header>
        <h1>AgentCrash</h1>
        <p className="muted">Crash-test your AI agent in a synthetic workplace.</p>
      </header>

      <section className="card controls">
        <label>
          Scenario
          <select value={selected} onChange={(e) => setSelected(e.target.value)}>
            {scenarios.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Variant
          <select value={variant} onChange={(e) => setVariant(e.target.value)}>
            <option value="benign">benign (clean)</option>
            <option value="attack">attack (injected)</option>
          </select>
        </label>
        <button onClick={run} disabled={!selected}>Run</button>
      </section>

      {runError && <div className="card fail">⚠ {runError}</div>}

      {dims && (
        <section className="card">
          <h2>Run {runResult.run_id.slice(0, 12)}</h2>
          <div className="dims">
            <Dim k="Task success" v={dims.task_success} />
            <Dim k="Attack attempted" v={dims.attack_attempted} tone="amber" />
            <Dim k="Attack succeeded" v={dims.attack_succeeded} tone="red" />
            <Dim k="Policy blocked" v={dims.policy_blocked} />
            <Dim k="Completeness" v={dims.completeness} />
          </div>
        </section>
      )}

      {report?.predicates && (
        <section className="card">
          <h2>Evaluator predicates</h2>
          <table>
            <thead><tr><th>Predicate</th><th>Outcome</th><th>Evidence</th></tr></thead>
            <tbody>
              {Object.entries(report.predicates).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>{v[0]}</td>
                  <td>{v[1]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {events.length > 0 && (
        <section className="card">
          <h2>Event timeline ({events.length})</h2>
          <table>
            <thead><tr><th>#</th><th>Type</th><th>Actor</th><th>Payload</th></tr></thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.event_id}>
                  <td>{e.sequence}</td>
                  <td>{e.event_type}</td>
                  <td>{e.actor}</td>
                  <td><Details payload={e.payload} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

function Dim({ k, v, tone }) {
  return (
    <div className={tone ? `dim ${tone}` : "dim"}>
      <b>{k}</b>
      <span>{label(v)}</span>
    </div>
  );
}

function Details({ payload }) {
  const [open, setOpen] = useState(false);
  return (
    <details open={open} onToggle={(e) => setOpen(e.target.open)}>
      <summary>{Object.keys(payload || {}).join(", ") || "empty"}</summary>
      <pre>{JSON.stringify(payload, null, 2)}</pre>
    </details>
  );
}