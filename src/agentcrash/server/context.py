"""Application context: shared paths and store wiring for the CLI/server.

Run data lives under the OS user data dir, not inside the repository.
Provider keys are never stored here.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..evidence.store import BlobStore, EventStore

DEFAULT_SCENARIOS: str = r"C:\Users\prath\OneDrive\Desktop\AgentCrash\scenarios"


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "agentcrash"


def get_scenarios_root(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("AGENTCRASH_SCENARIOS")
    if env:
        return env
    # A repository checkout is preferred so scenarios stay versioned with code.
    if Path(DEFAULT_SCENARIOS).is_dir():
        return DEFAULT_SCENARIOS
    return str(Path(user_data_dir()) / "scenarios")


def open_store(data_dir: str | None = None) -> tuple[EventStore, BlobStore, Path]:
    root = Path(data_dir) if data_dir else user_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    store = EventStore(root / "agentcrash.db")
    blobs = BlobStore(root / "blobs")
    return store, blobs, root