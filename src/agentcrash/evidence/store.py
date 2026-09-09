"""Authoritative event store for AgentCrash runs.

SQLite holds runs, events, findings, trial groups. JSONL is the portable
append-oriented export. Large payloads live in a run-scoped blob directory
addressed by digest so diagnostics don't need raw content.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..schemas.models import EventRecord

EVENT_TYPES = {
    "run.started",
    "model.requested",
    "model.completed",
    "tool.requested",
    "tool.rejected",
    "policy.decided",
    "tool.executed",
    "world.changed",
    "agent.completed",
    "evaluator.completed",
    "run.cancelled",
    "run.failed",
    "run.finalized",
}

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    scenario_version TEXT NOT NULL,
    variant TEXT NOT NULL,
    adapter TEXT NOT NULL,
    policy_id TEXT,
    model TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finalized_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    tool_call_id TEXT,
    parent_event_id TEXT,
    payload_ref TEXT,
    payload_digest TEXT,
    trust TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (run_id, sequence)
);
CREATE TABLE IF NOT EXISTS findings (
    run_id TEXT NOT NULL,
    trial_index INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    outcome TEXT NOT NULL,
    evidence TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
"""


def digest_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def digest_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class EventStore:
    """SQLite-backed event store. Thread-safe via a per-connection lock."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the local API runs sync endpoints in a
        # threadpool; the per-connection lock below serializes access.
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def record_run(
        self,
        run_id: str,
        scenario_id: str,
        scenario_version: str,
        variant: str,
        adapter: str,
        model: str,
        policy_id: str | None,
        status: str,
        created_at: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)",
                (run_id, scenario_id, scenario_version, variant, adapter,
                 policy_id, model, status, created_at, None),
            )
            self._conn.commit()

    def update_run_status(self, run_id: str, status: str, finalized_at: str | None = None) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE runs SET status=?, finalized_at=COALESCE(?, finalized_at) WHERE run_id=?",
                (status, finalized_at, run_id),
            )
            self._conn.commit()

    def patch_event_payload(self, run_id: str, event_type: str, new_payload: dict[str, Any]) -> None:
        """Rewrite the payload of the most recent event of a given type (used to
        correct the finalized record's dimensions after completeness settles)."""
        payload_json = json.dumps(new_payload, separators=(",", ":"))
        with self._lock:
            row = self._conn.execute(
                "SELECT MAX(sequence) FROM events WHERE run_id=? AND event_type=?",
                (run_id, event_type),
            ).fetchone()
            if row and row[0] is not None:
                self._conn.execute(
                    "UPDATE events SET payload=? WHERE run_id=? AND event_type=? AND sequence=?",
                    (payload_json, run_id, event_type, row[0]),
                )
                self._conn.commit()

    def append_event(self, ev: EventRecord) -> None:
        if ev.event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event type {ev.event_type}")
        payload_json = json.dumps(ev.payload, separators=(",", ":"))
        with self._lock:
            self._conn.execute(
                "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    ev.run_id, ev.sequence, ev.event_id, ev.event_type, ev.actor,
                    ev.timestamp, ev.tool_call_id, ev.parent_event_id,
                    ev.payload_ref, ev.payload_digest, ev.trust, payload_json,
                ),
            )
            self._conn.commit()

    def append_events(self, events: Iterable[EventRecord]) -> None:
        for ev in events:
            self.append_event(ev)

    def events(self, run_id: str) -> list[EventRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE run_id=? ORDER BY sequence", (run_id,)
            ).fetchall()
        return [_row_to_event(r) for r in rows]

    def add_finding(self, run_id: str, trial_index: int, dimension: str, outcome: str, evidence: str | None) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO findings VALUES (?,?,?,?,?)",
                (run_id, trial_index, dimension, outcome, evidence),
            )
            self._conn.commit()

    def runs(self) -> list[dict[str, Any]]:
        cols = ("run_id", "scenario_id", "scenario_version", "variant", "adapter",
                "policy_id", "model", "status", "created_at", "finalized_at")
        with self._lock:
            rows = self._conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        return [dict(zip(cols, r, strict=True)) for r in rows]


def _row_to_event(row: sqlite3.Row) -> EventRecord:
    payload = json.loads(row[11])
    return EventRecord(
        run_id=row[0],
        sequence=row[1],
        event_id=row[2],
        event_type=row[3],
        actor=row[4],
        timestamp=row[5],
        tool_call_id=row[6],
        parent_event_id=row[7],
        payload_ref=row[8],
        payload_digest=row[9],
        trust=row[10],
        payload=payload,
    )


def export_jsonl(store: EventStore, run_id: str) -> str:
    """Portable JSONL export of a run's events (one event per line)."""
    lines = []
    for ev in store.events(run_id):
        lines.append(json.dumps(ev.__dict__, default=str))
    return "\n".join(lines) + "\n"


class BlobStore:
    """Run-scoped blob storage addressed by content digest."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes) -> str:
        d = digest_bytes(data)
        (self.root / d).write_bytes(data)
        return d

    def put_text(self, text: str) -> str:
        return self.put(text.encode("utf-8"))

    def get(self, digest: str) -> bytes:
        return (self.root / digest).read_bytes()