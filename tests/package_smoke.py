"""Smoke-test an installed banip distribution artifact."""

from __future__ import annotations

import subprocess
from importlib.metadata import version

import banip
import banip.app


def main() -> None:
    """Verify imports, metadata, and console entry points."""
    package_version = version("banip")
    assert banip.__file__
    assert banip.app.__file__

    version_result = subprocess.run(
        ("banip", "--version"),
        check=True,
        capture_output=True,
        text=True,
    )
    assert version_result.stdout.strip() == f"banip {package_version}"

    help_result = subprocess.run(
        ("banip", "--help"),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "usage: banip" in help_result.stdout


if __name__ == "__main__":
    main()
