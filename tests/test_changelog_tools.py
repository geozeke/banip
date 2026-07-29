"""Tests for changelog and release-maintenance helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import bump_version as bump_version_script  # noqa: E402
from scripts import tag_release as tag_release_script  # noqa: E402
from scripts import update_latest_tag as latest_tag_script  # noqa: E402
from scripts import validate_release as validate_release_script  # noqa: E402
from scripts.changelog_tools import (  # noqa: E402
    Section,
    archive_changelog,
    extract_release_notes,
    has_release_entries,
    merge_unreleased,
    parse_version,
    validate_changelog_collection,
    validate_commit_title,
    validate_project_version,
)

PREAMBLE = "# Changelog\n\nRelease history."


def release(version: str, note: str = "Changed") -> str:
    """Return a minimal release section."""
    return f"## [{version}] - 2026-07-20\n\n### Changed\n\n- {note}"


@pytest.mark.parametrize(
    "version",
    ("0.1.0", "1.2.3b1", "2.0.0rc2"),
)
def test_parse_version_accepts_supported_pep440(version: str) -> None:
    """Supported stable and prerelease versions parse."""
    assert parse_version(version).text == version


@pytest.mark.parametrize(
    "version",
    (
        "v1.2.3",
        "1.2",
        "1.2.3+build",
        "01.2.3",
        "1.2.3-rc.1",
        "1.2.3rc01",
    ),
)
def test_parse_version_rejects_unsupported_values(version: str) -> None:
    """Noncanonical or unsupported release versions are rejected."""
    with pytest.raises(ValueError, match="PEP 440"):
        parse_version(version)


@pytest.mark.parametrize(
    "title",
    (
        "feat: add bot ranges",
        "fix(cli): validate the country",
        "deploy(release)!: rename the tag",
        "build(deps-dev): bump pytest",
        "security: reject unsafe plugin output",
    ),
)
def test_validate_commit_title_accepts_documented_types(title: str) -> None:
    """Documented Conventional Commit titles are accepted."""
    validate_commit_title(title)


@pytest.mark.parametrize(
    "title",
    ("Add bot ranges", "unknown: change", "fix(): empty scope", "fix missing colon"),
)
def test_validate_commit_title_rejects_invalid_titles(title: str) -> None:
    """Unclassified and malformed titles are rejected."""
    with pytest.raises(ValueError, match="Conventional Commit"):
        validate_commit_title(title)


def test_merge_unreleased_combines_matching_groups() -> None:
    """A curated baseline merges with generated release notes."""
    generated = Section("2.1.0", release("2.1.0", "Generated entry"))
    curated = Section(
        "Unreleased",
        "## [Unreleased]\n\n### Changed\n\n- Curated entry\n\n"
        "### Security\n\n- Safe by default",
    )

    merged = merge_unreleased(generated, curated)

    assert merged.text.count("### Changed") == 1
    assert "- Curated entry\n- Generated entry" in merged.text
    assert "### Security" in merged.text
    assert has_release_entries(merged)


def test_archive_changelog_moves_inactive_minor_lines(tmp_path: Path) -> None:
    """A new minor line archives older releases and retains the active line."""
    changelog = tmp_path / "CHANGELOG.md"
    archives = tmp_path / "changelogs"
    changelog.write_text(
        f"{PREAMBLE}\n\n{release('2.1.0')}\n\n{release('2.0.1')}\n\n"
        f"{release('2.0.0')}\n",
        encoding="utf-8",
    )

    updated = archive_changelog("2.1.0", changelog, archives)

    assert updated == [archives / "v2.0.x.md"]
    active = changelog.read_text(encoding="utf-8")
    assert "[2.1.0]" in active
    assert "[2.0.1]" not in active
    archived = updated[0].read_text(encoding="utf-8")
    assert archived.index("[2.0.1]") < archived.index("[2.0.0]")


def test_archive_changelog_keeps_patch_and_prerelease_line(tmp_path: Path) -> None:
    """Patch and prerelease entries remain together in the active minor line."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"{PREAMBLE}\n\n{release('2.1.0')}\n\n{release('2.1.0rc1')}\n",
        encoding="utf-8",
    )

    assert archive_changelog("2.1.0", changelog, tmp_path / "changelogs") == []
    assert "[2.1.0rc1]" in changelog.read_text(encoding="utf-8")


def test_extract_release_notes_uses_active_then_archive(tmp_path: Path) -> None:
    """Release notes are found in active and archived changelogs."""
    changelog = tmp_path / "CHANGELOG.md"
    archives = tmp_path / "changelogs"
    archives.mkdir()
    changelog.write_text(
        f"{PREAMBLE}\n\n{release('2.1.0', 'Active')}\n", encoding="utf-8"
    )
    (archives / "v2.0.x.md").write_text(
        f"# Changelog archive: 2.0.x\n\nArchive.\n\n{release('2.0.0', 'Archived')}\n",
        encoding="utf-8",
    )

    assert "- Active" in extract_release_notes("v2.1.0", changelog, archives)
    archived = extract_release_notes("v2.0.0", changelog, archives)
    assert "- Archived" in archived
    assert "## [2.0.0]" not in archived


def test_extract_release_notes_rejects_missing_and_empty_notes(
    tmp_path: Path,
) -> None:
    """Missing and empty release sections fail closed."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"{PREAMBLE}\n\n## [2.0.0] - 2026-07-20\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="empty"):
        extract_release_notes("v2.0.0", changelog, tmp_path / "changelogs")
    with pytest.raises(ValueError, match="not found"):
        extract_release_notes("v2.1.0", changelog, tmp_path / "changelogs")


def test_validate_changelog_collection_rejects_unknown_group(
    tmp_path: Path,
) -> None:
    """Only current changelog categories are accepted."""
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"{PREAMBLE}\n\n## [2.0.0] - 2026-07-20\n\n"
        "### 🚀 Features\n\n- Legacy heading.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported"):
        validate_changelog_collection(changelog, tmp_path / "changelogs")


def test_repository_changelogs_use_current_format() -> None:
    """Every tracked changelog passes the current collection validator."""
    validate_changelog_collection(
        PROJECT_ROOT / "CHANGELOG.md",
        PROJECT_ROOT / "changelogs",
        "2.0.1",
    )


def write_version_files(project_root: Path, version: str = "2.0.0") -> None:
    """Write minimal synchronized project metadata for release tests."""
    (project_root / "pyproject.toml").write_text(
        f'[project]\nname = "banip"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (project_root / "uv.lock").write_text(
        f'version = 1\n\n[[package]]\nname = "banip"\nversion = "{version}"\n',
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("version", "prerelease"),
    (("2.1.0", "false"), ("2.1.0rc1", "true")),
)
def test_write_github_outputs_classifies_release(
    version: str,
    prerelease: str,
    tmp_path: Path,
) -> None:
    """Validated PEP 440 versions select exactly one publication path."""
    output = tmp_path / "github-output"

    validate_release_script.write_github_outputs(output, parse_version(version))

    assert output.read_text(encoding="utf-8").splitlines() == [
        f"version={version}",
        f"prerelease={prerelease}",
    ]


def run_git(project_root: Path, *args: str) -> str:
    """Run Git in a temporary release repository."""
    return subprocess.run(
        ("git", *args),
        cwd=project_root,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def create_release_repository(tmp_path: Path) -> Path:
    """Create a clean main branch with a local bare origin."""
    project_root = tmp_path / "project"
    origin = tmp_path / "origin.git"
    project_root.mkdir()
    run_git(project_root, "init", "--initial-branch=main")
    run_git(project_root, "config", "user.name", "Release Test")
    run_git(project_root, "config", "user.email", "release@example.test")
    write_version_files(project_root)
    (project_root / "changelogs").mkdir()
    (project_root / "CHANGELOG.md").write_text(
        f"{PREAMBLE}\n\n{release('2.0.0', 'First release')}\n",
        encoding="utf-8",
    )
    run_git(project_root, "add", ".")
    run_git(project_root, "commit", "--message", "chore(release): prepare for 2.0.0")
    subprocess.run(
        ("git", "init", "--bare", str(origin)),
        check=True,
        capture_output=True,
    )
    run_git(project_root, "remote", "add", "origin", str(origin))
    run_git(project_root, "push", "--set-upstream", "origin", "main")
    return project_root


def test_validate_project_version_rejects_mismatched_metadata(
    tmp_path: Path,
) -> None:
    """Release validation fails when project versions drift."""
    write_version_files(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "banip"\nversion = "2.1.0"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not synchronized"):
        validate_project_version(tmp_path)


def test_validate_project_version_accepts_pep440_prerelease(
    tmp_path: Path,
) -> None:
    """PEP 440 project metadata matches its release version exactly."""
    write_version_files(tmp_path, "2.1.0rc1")

    assert validate_project_version(tmp_path, "2.1.0rc1") == "2.1.0rc1"


def test_tag_release_creates_and_pushes_annotated_tag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid release creates one annotated tag on the matching origin."""
    project_root = create_release_repository(tmp_path)
    monkeypatch.setattr(tag_release_script, "PROJECT_ROOT", project_root)

    tag = tag_release_script.tag_release()

    assert tag == "v2.0.0"
    assert run_git(project_root, "cat-file", "-t", tag) == "tag"
    assert run_git(project_root, "ls-remote", "--tags", "origin", f"refs/tags/{tag}")


def test_tag_release_rejects_untracked_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untracked files make release tagging fail closed."""
    project_root = create_release_repository(tmp_path)
    (project_root / "untracked.txt").write_text("dirty", encoding="utf-8")
    monkeypatch.setattr(tag_release_script, "PROJECT_ROOT", project_root)

    with pytest.raises(ValueError, match="clean"):
        tag_release_script.tag_release()


def test_release_commit_validation_rejects_nonconventional_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release preparation rejects direct non-Conventional commits."""
    monkeypatch.setattr(
        bump_version_script,
        "release_commit_start",
        lambda tags: "v2.0.0",
    )

    def fake_run(*args: str, capture: bool = False) -> str:
        assert args == (
            "git",
            "log",
            "v2.0.0..HEAD",
            "--no-merges",
            "--format=%s",
        )
        assert capture
        return "feat: valid change\nPlain-language commit\n"

    monkeypatch.setattr(bump_version_script, "run", fake_run)

    with pytest.raises(ValueError, match="Plain-language commit"):
        bump_version_script.validate_release_commits(["v2.0.0"])


def test_prepare_changelog_uses_generated_preamble(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Release preparation retains git-cliff's configured preamble."""
    generated_preamble = "# Changelog\n\nProject versions follow PEP 440."
    (tmp_path / "CHANGELOG.md").write_text(
        f"{PREAMBLE}\n\n{release('2.0.0', 'Current')}\n",
        encoding="utf-8",
    )
    destination = tmp_path / "prepared.md"

    def fake_run(*args: str, capture: bool = False) -> str:
        assert args == (
            "git-cliff",
            "--unreleased",
            "--tag",
            "v2.1.0rc1",
        )
        assert capture
        return f"{generated_preamble}\n\n{release('2.1.0rc1', 'Candidate')}\n"

    monkeypatch.setattr(bump_version_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bump_version_script, "run", fake_run)

    bump_version_script.prepare_changelog(
        "2.1.0rc1",
        destination,
        tmp_path / "archives",
    )

    assert destination.read_text(encoding="utf-8").startswith(
        f"{generated_preamble}\n\n## [2.1.0rc1]"
    )


def test_bump_restores_versions_after_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed metadata command restores every file changed by the bump."""
    write_version_files(tmp_path)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        f"{PREAMBLE}\n\n{release('2.0.0', 'Current')}\n",
        encoding="utf-8",
    )
    archives = tmp_path / "changelogs"
    archives.mkdir()
    version_paths = (
        tmp_path / "pyproject.toml",
        tmp_path / "uv.lock",
        changelog,
    )
    originals = {path: path.read_bytes() for path in version_paths}

    def fake_run(*args: str, capture: bool = False) -> str:
        if args[:2] == ("git", "tag"):
            return "v2.0.0\n"
        if args[:2] == ("uv", "version"):
            (tmp_path / "pyproject.toml").write_text("changed", encoding="utf-8")
            (tmp_path / "uv.lock").write_text("changed", encoding="utf-8")
            raise subprocess.CalledProcessError(1, args)
        raise AssertionError(f"Unexpected command: {args}, capture={capture}")

    def fake_prepare(
        version: str,
        destination: Path,
        archive_dir: Path,
        promotion_from: str | None = None,
    ) -> None:
        del archive_dir, promotion_from
        destination.write_text(
            f"{PREAMBLE}\n\n{release(version, 'Prepared')}\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(bump_version_script, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(bump_version_script, "run", fake_run)
    monkeypatch.setattr(bump_version_script, "require_clean_tree", lambda: None)
    monkeypatch.setattr(
        bump_version_script,
        "validate_release_commits",
        lambda tags: None,
    )
    monkeypatch.setattr(bump_version_script, "prepare_changelog", fake_prepare)
    monkeypatch.setattr(bump_version_script.shutil, "which", lambda command: command)

    with pytest.raises(subprocess.CalledProcessError):
        bump_version_script.bump("2.1.0")

    assert {path: path.read_bytes() for path in version_paths} == originals


def test_update_latest_tag_moves_only_latest_stable_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The mutable tag moves only for GitHub's latest stable release."""
    commands: list[tuple[str, ...]] = []

    def fake_run(
        args: tuple[str, ...],
        *,
        cwd: Path,
        check: bool,
    ) -> None:
        assert cwd == latest_tag_script.PROJECT_ROOT
        assert check
        commands.append(args)

    monkeypatch.setattr(latest_tag_script.subprocess, "run", fake_run)

    assert latest_tag_script.update_latest_tag("v2.1.0", "v2.1.0", "abc123")
    assert commands == [
        ("git", "tag", "--force", "latest", "abc123"),
        ("git", "push", "--force", "origin", "refs/tags/latest"),
    ]


@pytest.mark.parametrize(
    ("candidate", "latest_release"),
    (
        ("v2.1.0b1", "v2.0.1"),
        ("v2.1.0rc1", "v2.0.1"),
        ("v2.0.1", "v2.1.0"),
    ),
)
def test_update_latest_tag_ignores_prerelease_and_older_release(
    candidate: str,
    latest_release: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prereleases and older stable workflow reruns cannot move latest."""

    def fail_run(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"Unexpected Git command: {args}, {kwargs}")

    monkeypatch.setattr(latest_tag_script.subprocess, "run", fail_run)

    assert not latest_tag_script.update_latest_tag(
        candidate,
        latest_release,
        "abc123",
    )
