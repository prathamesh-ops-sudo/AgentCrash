"""Public, versioned contracts for AgentCrash.

These live in `schemas` and must not depend on provider SDKs. Version every
schema independently from the package version.
"""

SCHEMA_VERSION = 1
PACKAGE_VERSION = "0.1.2"

__all__ = ["SCHEMA_VERSION", "PACKAGE_VERSION"]