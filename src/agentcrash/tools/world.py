"""Synthetic world state for a scenario run.

The world fixture defines stable synthetic record IDs and the initial clean
task state. Every trial starts from an immutable copy of the fixture; a rerun
never rewinds a live service or reuses a mutated workspace.
"""
from __future__ import annotations

import copy
from typing import Any


class WorldState:
    """Immutable-initialized world snapshot that records authoritative changes.

    The world owns canonical state: documents (readable records), notes, and an
    outbox (simulated mail). Outbound mail and uploads are written to this local
    sink, never to a real external recipient.
    """

    def __init__(self, fixture: dict[str, Any]) -> None:
        # deep copy so the passed fixture is never mutated by the run
        self._state: dict[str, Any] = copy.deepcopy(fixture)

        # Ensure canonical top-level sections exist.
        self._state.setdefault("documents", {})
        self._state.setdefault("notes", {})
        self._state.setdefault("outbox", [])
        self._state.setdefault("metadata", {})

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    def snapshot(self) -> dict[str, Any]:
        """Deep copy for diffing / evidence snapshots."""
        return copy.deepcopy(self._state)

    # --- canonical reads ---
    def list_documents(self) -> list[str]:
        return list(self._state["documents"].keys())

    def read_document(self, document_id: str) -> dict[str, Any] | None:
        return self._state.setdefault("documents", {}).get(document_id)

    def documents(self) -> dict[str, Any]:
        return self._state["documents"]

    def notes(self) -> dict[str, Any]:
        return self._state["notes"]

    def get_note(self, note_id: str) -> Any | None:
        return self._state["notes"].get(note_id)

    def outbox(self) -> list[dict[str, Any]]:
        return list(self._state["outbox"])

    # --- canonical writes (recorded as authoritative world.changed events) ---
    def write_note(self, note_id: str, content: Any) -> None:
        self._state.setdefault("notes", {})[note_id] = copy.deepcopy(content)

    def delete_note(self, note_id: str) -> bool:
        if note_id in self._state.get("notes", {}):
            del self._state["notes"][note_id]
            return True
        return False

    def append_outbox(self, entry: dict[str, Any]) -> None:
        self._state.setdefault("outbox", []).append(copy.deepcopy(entry))

    def set_document(self, document_id: str, content: str) -> None:
        self._state.setdefault("documents", {})[document_id] = {"content": content}

    def metadata(self) -> dict[str, Any]:
        return self._state["metadata"]


def apply_world_patch(world: WorldState, path: str, value: Any) -> None:
    """Apply a dotted-file path write, e.g. 'notes.invoice_summary'. Overwrites."""
    parts = path.split(".")
    target: Any = world._state
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = copy.deepcopy(value)