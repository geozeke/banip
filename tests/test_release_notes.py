"""Tests for release-note extraction."""

from pathlib import Path
import subprocess as sp


def test_extract_release_notes_for_current_changelog(tmp_path: Path) -> None:
    """Release-note extraction supports the current changelog format."""
    output_file = tmp_path / "notes.md"

    result = sp.run(
        ["sh", "scripts/extract_release_notes.sh", "v1.4.1", str(output_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    notes = output_file.read_text()
    assert notes.startswith("## 1.4.1 ")
    assert "Runtime Dependencies" in notes


def test_extract_release_notes_rejects_non_version_tag(tmp_path: Path) -> None:
    """Release-note extraction requires version tags to start with v."""
    output_file = tmp_path / "notes.md"

    result = sp.run(
        ["sh", "scripts/extract_release_notes.sh", "latest", str(output_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "tag must start with 'v'" in result.stderr


def test_extract_release_notes_finds_archived_changelog_entries(
    tmp_path: Path,
) -> None:
    """Release-note extraction can read archived minor changelogs."""
    output_file = tmp_path / "notes.md"

    result = sp.run(
        ["sh", "scripts/extract_release_notes.sh", "v1.3.12", str(output_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    notes = output_file.read_text()
    assert notes.startswith("## 1.3.12 ")
    assert "Runtime Dependencies" in notes
