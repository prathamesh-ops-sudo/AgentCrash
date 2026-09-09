"""Scenario loader: validate data-only packs and resolve them into Scenario.

Packs are directories containing scenario.yaml (or scenario.yml), fixture
files, and optional scripted trace files. Loading rejects scripts, unsafe
YAML, and executable entries — packs are data only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from ..schemas.scenario import Scenario, ScenarioLoadError, ScenarioManifest

_MANIFEST_NAMES = ("scenario.yaml", "scenario.yml")


def _load_yaml_safe(path: Path) -> dict:
    """Safe YAML loader; rejects executable/constructor tags.

    `yaml.SafeLoader` refuses implicit python/constructor tags and never
    executes them. Add explicit constructors for the common hostile tags so
    they raise a clear error instead of returning None.
    """
    def _no_constructor(loader: yaml.Loader, suffix: str, node: Any) -> Any:
        raise ScenarioLoadError(f"{path}: constructor tag !{suffix} not allowed")

    class _Safe(yaml.SafeLoader):  # type: ignore[misc]
        pass

    _Safe.add_constructor("!python/object", _no_constructor)
    _Safe.add_constructor("!python/name", _no_constructor)
    _Safe.add_constructor("!!python/object", _no_constructor)

    try:
        data = yaml.load(path.read_text(), Loader=_Safe)
    except yaml.YAMLError as exc:
        raise ScenarioLoadError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ScenarioLoadError(f"{path}: manifest root must be a mapping")
    return data


def _resolve_file(basedir: Path, name: str) -> str:
    path = (basedir / name).resolve()
    # Path confinement: resolved path must stay inside the pack dir.
    if not str(path).startswith(str(basedir.resolve())):
        raise ScenarioLoadError(f"{name}: file escapes pack directory (denied)")
    if not path.exists():
        raise ScenarioLoadError(f"{name}: fixture file not found")
    return path.read_text()


def _resolve_json(basedir: Path, name: str) -> Any:
    text = _resolve_file(basedir, name)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScenarioLoadError(f"{name}: invalid JSON fixture: {exc}") from exc


def _load_trace(basedir: Path, name: str | None) -> list[dict[str, Any]]:
    if not name:
        return []
    raw = _resolve_json(basedir, name)
    if not isinstance(raw, list):
        raise ScenarioLoadError(f"{name}: trace must be a JSON list of decisions")
    return raw


def load_scenario(pack_dir: str | Path) -> Scenario:
    basedir = Path(pack_dir).resolve()
    if not basedir.is_dir():
        raise ScenarioLoadError(f"{basedir}: not a directory")
    manifest_path = next((basedir / n for n in _MANIFEST_NAMES if (basedir / n).is_file()), None)
    if manifest_path is None:
        raise ScenarioLoadError(f"{basedir}: no scenario.yaml manifest found")

    data = _load_yaml_safe(manifest_path)
    try:
        manifest = ScenarioManifest.model_validate(data)
    except Exception as exc:
        raise ScenarioLoadError(f"{manifest_path}: manifest validation failed: {exc}") from exc

    task_text = _resolve_file(basedir, manifest.task_file) if manifest.task_file else ""
    world = _resolve_json(basedir, manifest.world_fixture)
    injection_content = None
    if manifest.injection and manifest.injection.replacement_file:
        injection_content = _resolve_file(basedir, manifest.injection.replacement_file)

    benign = _load_trace(basedir, manifest.benign_trace)
    attack = _load_trace(basedir, manifest.attack_trace)
    blocked = _load_trace(basedir, manifest.blocked_trace)

    return Scenario(
        manifest=manifest,
        basedir=str(basedir),
        task_text=task_text,
        world=world,
        injection_content=injection_content,
        benign_trace=benign,
        attack_trace=attack,
        blocked_trace=blocked,
    )


def discover_packs(scenarios_root: str | Path) -> list[str]:
    root = Path(scenarios_root).resolve()
    if not root.is_dir():
        return []
    packs = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and any((child / n).is_file() for n in _MANIFEST_NAMES):
            packs.append(child.name)
    return packs