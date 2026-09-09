"""Sandbox profile validation tests. These confirm the invariants that must
never be weakened, and are part of the release blockers.
"""
import pytest

from agentcrash.sandbox.launcher import Launcher
from agentcrash.sandbox.profile import (
    DEFAULT_PROFILE,
    ContainerProfile,
    ProfileError,
    validate_profile,
)


def test_default_profile_valid():
    validate_profile(DEFAULT_PROFILE)


def test_privileged_rejected():
    p = ContainerProfile(privileged=True)
    with pytest.raises(ProfileError):
        validate_profile(p)


def test_root_user_rejected():
    p = ContainerProfile(user="root")
    with pytest.raises(ProfileError):
        validate_profile(p)


def test_host_network_rejected():
    p = ContainerProfile(network_namespace_host=True)
    with pytest.raises(ProfileError):
        validate_profile(p)


def test_host_pid_rejected():
    p = ContainerProfile(pid_namespace_host=True)
    with pytest.raises(ProfileError):
        validate_profile(p)


def test_writable_root_rejected():
    p = ContainerProfile(read_only_rootfs=False)
    with pytest.raises(ProfileError):
        validate_profile(p)


def test_docker_socket_mount_rejected():
    p = ContainerProfile(mounts=[{"source": "/var/run/docker.sock",
                                  "target": "/var/run/docker.sock"}])
    with pytest.raises(ProfileError):
        validate_profile(p)


def test_launch_spec_locks_capabilities():
    spec = DEFAULT_PROFILE.to_launch_spec()
    assert spec["cap_drop"] == ["ALL"]
    assert spec["privileged"] is False
    assert spec["read_only"] is True
    assert spec["pid_host"] is False
    assert spec["network_host"] is False


def test_launcher_preflight_reports_availability():
    # preflight must not blow up; it reports whether the runtime is present.
    launcher = Launcher(DEFAULT_PROFILE)
    result = launcher.preflight()
    assert "available" in result and "validated" in result
    assert result["validated"] is True