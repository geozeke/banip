"""Verify that every direct dependency has an approved license record."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"^[A-Za-z0-9_.-]+")
APPROVED = {
    "Apache-2.0",
    "Apache-2.0 OR MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "MIT",
    "MIT-CMU",
    "PSF-2.0",
}


def dependency_name(requirement: str) -> str:
    """Extract and normalize a package name from a PEP 508 requirement."""
    match = NAME.match(requirement)
    if match is None:
        raise ValueError(f"Invalid dependency requirement: {requirement}")
    return match.group().lower().replace("_", "-")


def main() -> None:
    """Compare dependency manifests with the reviewed license inventory."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    python_requirements = [
        *project["project"]["dependencies"],
        *project["build-system"]["requires"],
    ]
    for group in project["dependency-groups"].values():
        python_requirements.extend(group)
    python_dependencies = {
        dependency_name(requirement) for requirement in python_requirements
    }

    action_dependencies: set[str] = set()
    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        action_dependencies.update(
            action
            for action in re.findall(
                r"(?m)^\s+-?\s*uses:\s+([^@\s]+)@[^\s]+",
                workflow.read_text(),
            )
            if not action.startswith("./")
        )

    inventory = tomllib.loads(
        (ROOT / "config" / "dependency-licenses.toml").read_text()
    )
    problems: list[str] = []
    for ecosystem, expected, recorded in (
        ("Python", python_dependencies, set(inventory["python"])),
        ("GitHub Actions", action_dependencies, set(inventory["actions"])),
    ):
        if missing := sorted(expected - recorded):
            problems.append(
                f"{ecosystem} dependencies missing license records: {missing}"
            )
        if extra := sorted(recorded - expected):
            problems.append(f"Stale {ecosystem} license records: {extra}")
    for ecosystem in ("python", "actions"):
        for dependency, license_name in inventory[ecosystem].items():
            if license_name not in APPROVED:
                problems.append(
                    f"{dependency} uses unapproved license {license_name!r}"
                )
    if problems:
        raise SystemExit("\n".join(problems))
    print("All direct dependencies have approved license records.")


if __name__ == "__main__":
    main()
