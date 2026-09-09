"""Policy loader: safe YAML parsing of policy manifests.

Unknown policy constructs fail configuration validation; they are never
silently ignored. Digest is computed on canonical serialization.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..schemas.policy import PolicyManifest, PolicyParseError


def load_policy(path: str | Path) -> PolicyManifest:
    p = Path(path)
    if not p.is_file():
        raise PolicyParseError(f"{p}: policy file not found")
    try:
        data = yaml.safe_load(p.read_text())
    except yaml.YAMLError as exc:
        raise PolicyParseError(f"{p}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise PolicyParseError(f"{p}: policy root must be a mapping")
    try:
        return PolicyManifest.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise PolicyParseError(f"{p}: policy validation failed: {exc}") from exc


def policy_digest(manifest: PolicyManifest) -> str:
    import hashlib

    return hashlib.sha256(manifest.digest_input.encode("utf-8")).hexdigest()


def load_policy_optional(path: str | None) -> PolicyManifest | None:
    return load_policy(path) if path else None