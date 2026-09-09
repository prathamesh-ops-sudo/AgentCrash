"""Fixed runtime profile for the AgentCrash worker.

The container profile is the hardware of containment: a non-root user, a
read-only root filesystem, dropped capabilities, no privileged mode, no host
PID or network namespace, a limited writable tmpfs, resource limits, and an
enabled seccomp policy. A Compose network flag alone is NOT a demonstrated
guarantee; the launcher must validate these properties.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PROFILE_NAME = "agentcrash-worker-default"
PROFILE_VERSION = 1
IMAGE = "python:3.12-slim"


@dataclass
class ContainerProfile:
    """Declaration of the fixed worker container profile."""

    name: str = PROFILE_NAME
    version: int = PROFILE_VERSION
    image: str = IMAGE
    user: str = "nobody"                      # non-root user
    read_only_rootfs: bool = True
    privileged: bool = False
    pid_namespace_host: bool = False          # no host PID namespace
    network_namespace_host: bool = False      # no host network namespace
    cap_drop: list[str] = field(default_factory=lambda: ["ALL"])
    seccomp: str = "unconfined"               # replaced by a real profile at launch
    tmpfs_writable: str = "/tmp:size=64m"     # bounded writable area
    mounts: list[dict[str, str]] = field(default_factory=list)  # fixed fixture mounts only
    resource_limits: dict[str, str] = field(default_factory=dict)
    internal_network: str | None = None    # run-scoped network for worker+tools

    def to_launch_spec(self) -> dict[str, Any]:
        """Fixed launch specification validated by the host-side launcher."""
        return {
            "profile": self.name,
            "image": self.image,
            "user": self.user,
            "read_only": self.read_only_rootfs,
            "privileged": self.privileged,
            "pid_host": self.pid_namespace_host,
            "network_host": self.network_namespace_host,
            "cap_drop": list(self.cap_drop),
            "seccomp": self.seccomp,
            "tmpfs": [self.tmpfs_writable],
            "mounts": list(self.mounts),
            "limits": dict(self.resource_limits),
            "network": self.internal_network,
        }


DEFAULT_PROFILE = ContainerProfile(
    seccomp="default",
    resource_limits={
        "memory": "512m",
        "pids": "64",
        "cpu": "0.5",
        "fs.inotify.max_user_watches": "1024",
    },
)


class ProfileError(Exception):
    pass


def validate_profile(profile: ContainerProfile) -> None:
    """Sanity-check invariants that must never be weakened."""
    if profile.privileged:
        raise ProfileError("privileged mode is never allowed in a supported profile")
    if profile.user == "root" or profile.user in ("",):
        raise ProfileError("worker must run as a non-root user")
    if profile.network_namespace_host:
        raise ProfileError("worker must not share the host network namespace")
    if profile.pid_namespace_host:
        raise ProfileError("worker must not share the host PID namespace")
    if not profile.read_only_rootfs:
        raise ProfileError("root filesystem must be read-only")
    # No Docker socket / daemon access, ever.
    for m in profile.mounts:
        target = str(m.get("target", "")).replace("\\", "/").lower()
        if "docker.sock" in target or "/var/run/" in target:
            raise ProfileError("mounting the container runtime socket is forbidden")