"""Run suite orchestration: trials, groups, comparison, and fixing.

`compare` aligns runs by scenario version, adapter digest, policy digest, model
identity, trial index, and warns when these differ.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from ..schemas.models import RunConfig, RunResultDimensions, TrialGroupMeta


@dataclass
class TrialOutcome:
    index: int
    run_id: str
    dims: RunResultDimensions
    attrs: dict[str, str]


def compute_digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def run_config_digest(config: RunConfig) -> str:
    me = "|".join([
        config.scenario_id, config.scenario_version, config.variant, config.adapter,
        config.policy_id or "", config.model,
    ])
    return compute_digest(me)


def summarize_trials(outcomes: list[TrialOutcome]) -> dict[str, Any]:
    """Per-scenario denominators + exclusions, never a hidden favorable fraction."""
    total = len(outcomes)
    evaluable = [o for o in outcomes if o.dims.completeness]
    attack_passes = sum(1 for o in outcomes if o.dims.attack_succeeded)
    utility_ok = sum(1 for o in outcomes if o.dims.task_success)
    attempted = sum(1 for o in outcomes if o.dims.attack_attempted)
    return {
        "trials_total": total,
        "trials_evaluable": len(evaluable),
        "trials_incomplete_or_error": total - len(evaluable),
        "attack_success_rate": (attack_passes / len(evaluable)) if evaluable else None,
        "attack_attempted_count": attempted,
        "task_success_count": utility_ok,
        "attack_success_count": attack_passes,
    }


def compare_groups(
    baseline: list[TrialOutcome],
    defended: list[TrialOutcome],
    baseline_meta: TrialGroupMeta,
    defended_meta: TrialGroupMeta,
) -> dict[str, Any]:
    warnings = baseline_meta.alignment_warnings(defended_meta)
    b = summarize_trials(baseline)
    d = summarize_trials(defended)
    improvement = None
    if b.get("attack_success_rate") is not None and d.get("attack_success_rate") is not None:
        improvement = b["attack_success_rate"] - d["attack_success_rate"]
    # The report makes 'blocked everything' easy to identify: utility must be
    # preserved, not just attacks stopped.
    utility_degraded = (b.get("task_success_count", 0) > 0 and
                        d.get("task_success_count", 0) < b.get("task_success_count", 0))
    return {
        "warnings": warnings,
        "baseline": b,
        "defended": d,
        "attack_success_reduction": improvement,
        "utility_degraded": utility_degraded,
    }