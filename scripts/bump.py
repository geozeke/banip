# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import subprocess as sp
import sys
from pathlib import Path

from archive_changelog import archive_changelog
from archive_changelog import normalize_changelog

BASE = Path(__file__).parents[1]
CHANGELOG = BASE / "CHANGELOG.md"
PYPROJECT = BASE / "pyproject.toml"
CHANGELOG_ARCHIVE = BASE / "changelogs"


def main() -> None:

    # Check command line arguments
    if len(sys.argv) != 2:
        print("Invalid number of command line arguments")
        sys.exit(1)

    # Normalize the version number
    new_version = sys.argv[1].lower()
    if new_version[0] == "v":
        new_version = new_version[1:]

    # Generate updated changelog entry.
    sp.run(
        ["git", "cliff", "--unreleased", "--tag", new_version, "--prepend", CHANGELOG],
        check=True,
    )

    # git-cliff's trimmed prepend output may not leave a blank line
    # before the previous release heading.
    normalize_changelog(CHANGELOG)

    # Keep CHANGELOG.md focused on the active minor line.
    archive_changelog(new_version, CHANGELOG, CHANGELOG_ARCHIVE)

    # Bump version in pyproject.toml
    with open(PYPROJECT, "r") as f:
        pyproject = [line.rstrip() for line in f]
    for i in range(len(pyproject)):
        if pyproject[i].startswith("version"):
            pyproject[i] = f'version = "{new_version}"'
            break
    with open(PYPROJECT, "w") as f:
        f.write("\n".join(pyproject) + "\n")


if __name__ == "__main__":
    main()
