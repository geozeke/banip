#!/usr/bin/env python3
"""Validate a release tag against metadata and committed release notes."""

from __future__ import annotations

import argparse
from pathlib import Path

from .changelog_tools import (
    extract_release_notes,
    parse_version,
    validate_changelog_collection,
    validate_project_version,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Validate the requested release tag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="Release tag in vX.Y.Z form.")
    args = parser.parse_args()
    if not args.tag.startswith("v"):
        parser.error("Release tag must start with v")
    try:
        version = parse_version(args.tag.removeprefix("v")).text
        validate_project_version(PROJECT_ROOT, version)
        validate_changelog_collection(
            PROJECT_ROOT / "CHANGELOG.md",
            PROJECT_ROOT / "changelogs",
            version,
        )
        extract_release_notes(
            args.tag,
            PROJECT_ROOT / "CHANGELOG.md",
            PROJECT_ROOT / "changelogs",
        )
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
