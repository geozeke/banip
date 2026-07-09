"""Tests for changelog archiving."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_changelog.py"
SPEC = importlib.util.spec_from_file_location("archive_changelog", SCRIPT_PATH)
assert SPEC is not None
archive_changelog = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = archive_changelog
SPEC.loader.exec_module(archive_changelog)


def test_parse_version_accepts_prerelease_versions() -> None:
    """Prerelease and build metadata do not affect major/minor parsing."""
    assert archive_changelog.parse_version("v1.5.0-beta.1") == (1, 5, 0)
    assert archive_changelog.parse_version("1.5.0-rc.1+build.5") == (1, 5, 0)


def test_patch_bump_does_not_archive_existing_old_sections(tmp_path: Path) -> None:
    """Patch bumps leave an already-mixed active changelog unchanged."""
    changelog = tmp_path / "CHANGELOG.md"
    archive_dir = tmp_path / "changelogs"
    original = """## 1.4.2 (2026-05-09)

### Fixed

- Patch release.

## 1.4.1 (2026-05-08)

### Fixed

- Previous patch.

## 1.3.0 (2026-04-22)

### Added

- Older minor entry.
"""
    changelog.write_text(original, encoding="utf-8")

    changed = archive_changelog.archive_changelog("v1.4.2", changelog, archive_dir)

    assert not changed
    assert changelog.read_text(encoding="utf-8") == original
    assert not archive_dir.exists()


def test_minor_bump_archives_old_sections_and_moves_links(tmp_path: Path) -> None:
    """Minor bumps archive older minor sections and preserve used links."""
    changelog = tmp_path / "CHANGELOG.md"
    archive_dir = tmp_path / "changelogs"
    changelog.write_text(
        """## 1.5.0 (2026-05-09)

### Added

- Current minor entry.

## 1.4.3 (2026-05-08)

### Fixed

- Previous minor entry.

## 1.3.0 (2026-04-22)

### Changed

- Older linked entry using [pkg][pkg].

[pkg]: https://example.test/pkg
""",
        encoding="utf-8",
    )

    changed = archive_changelog.archive_changelog("1.5.0", changelog, archive_dir)

    assert changed
    active = changelog.read_text(encoding="utf-8")
    assert "## 1.5.0" in active
    assert "## 1.4.3" not in active
    assert "[pkg]:" not in active

    archive_14 = (archive_dir / "v1.4.x.md").read_text(encoding="utf-8")
    assert "## 1.4.3" in archive_14

    archive_13 = (archive_dir / "v1.3.x.md").read_text(encoding="utf-8")
    assert "## 1.3.0 (2026-04-22)" in archive_13
    assert "[pkg]: https://example.test/pkg" in archive_13


def test_normalize_changelog_restores_release_spacing(tmp_path: Path) -> None:
    """Normalization restores blank lines between release sections."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        """## 2.0.1 (2026-07-09)

### Refactor

- Migrate utilities.
## 2.0.0 (2026-07-08)

### Added

- Previous release.
""",
        encoding="utf-8",
    )

    changed = archive_changelog.normalize_changelog(changelog)

    assert changed
    assert (
        changelog.read_text(encoding="utf-8")
        == """## 2.0.1 (2026-07-09)

### Refactor

- Migrate utilities.

## 2.0.0 (2026-07-08)

### Added

- Previous release.
"""
    )


def test_force_archives_for_initial_cleanup(tmp_path: Path) -> None:
    """Forced cleanup archives non-target minor lines immediately."""
    changelog = tmp_path / "CHANGELOG.md"
    archive_dir = tmp_path / "changelogs"
    changelog.write_text(
        """## 1.4.3 (2026-05-08)

### Fixed

- Current patch.

## 1.4.2 (2026-05-08)

### Changed

- Current minor patch.

## 1.3.0 (2026-04-22)

### Added

- Previous minor.
""",
        encoding="utf-8",
    )

    changed = archive_changelog.archive_changelog(
        "1.4.3",
        changelog,
        archive_dir,
        force=True,
    )

    assert changed
    active = changelog.read_text(encoding="utf-8")
    assert "## 1.4.3" in active
    assert "## 1.4.2" in active
    assert "## 1.3.0" not in active
    assert "## 1.3.0" in (archive_dir / "v1.3.x.md").read_text(encoding="utf-8")
