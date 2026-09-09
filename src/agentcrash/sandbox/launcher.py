"""Host-side launcher for the sandbox profile.

The trusted launcher uses the container runtime API after validating a fixed
launch specification. It never mounts a Docker socket inside the worker. In
v0.1 the launcher validates the profile and can drive Docker for systems where
the (pre-built) worker image exists; the deterministic default path runs
uncontained for demo/CI and is explicitly labeled as such.
"""
from __future__ import annotations

import subprocess
from typing import Any

from .profile import ContainerProfile, validate_profile


class Launcher:
    def __init__(self, profile: ContainerProfile, container_runtime: str = "docker") -> None:
        self.profile = profile
        self.runtime = container_runtime

    def preflight(self) -> dict[str, Any]:
        """Check the container runtime exists and the profile is valid."""
        validate_profile(self.profile)
        try:
            proc = subprocess.run([self.runtime, "info"],
                                  capture_output=True, text=True, timeout=30)
            ok = proc.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            ok = False
        return {
            "runtime": self.runtime,
            "available": ok,
            "profile": self.profile.name,
            "validated": True,
            "requires_sandbox": not ok,
        }

    def run_in_container(self, run_spec: dict[str, Any]) -> int:
        """Launch the worker in a container built from the fixed spec.

        Not used by the deterministic CI path. Requires a pre-built worker
        image and a working container runtime.
        """
        spec = self.profile.to_launch_spec()
        validate_profile(self.profile)
        cmd = [
            self.runtime, "run", "--rm",
            "--user", spec["user"],
            "--read-only",
            "--cap-drop", "ALL",
            "--memory", spec["limits"]["memory"],
            "--pids-limit", spec["limits"]["pids"],
            "--cpus", spec["limits"]["cpu"],
            "--security-opt", f"seccomp={spec['seccomp']}",
            "--tmpfs", spec["tmpfs"][0],
            self.profile.image,
            "python", "-c", run_spec.get("command", "pass"),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return proc.returncode