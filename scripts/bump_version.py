#!/usr/bin/env python3
"""Prepare an explicit application version and its generated changelog."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from .changelog_tools import (
    Section,
    archive_changelog,
    format_changelog,
    has_release_entries,
    merge_unreleased,
    parse_version,
    split_changelog,
    validate_changelog_collection,
    validate_commit_title,
    validate_project_version,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONVENTIONAL_BASELINE = "50a87b9642ebec71bc335ad6ac456df3bbfb809b"
VERSION_FILES = (Path("pyproject.toml"), Path("uv.lock"), Path("CHANGELOG.md"))


def run(*args: str, capture: bool = False) -> str:
    """Run a command from the project root and optionally return stdout."""
    result = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def require_clean_tree() -> None:
    """Require a clean tracked and untracked working tree."""
    if run("git", "status", "--porcelain=v1", "--untracked-files=all", capture=True):
        raise ValueError("Working tree must be clean before preparing a release")


def release_commit_start(tags: list[str]) -> str:
    """Return the newest release tag after the Conventional Commit baseline."""
    for tag in tags:
        result = subprocess.run(
            ("git", "merge-base", "--is-ancestor", CONVENTIONAL_BASELINE, tag),
            cwd=PROJECT_ROOT,
            check=False,
        )
        if result.returncode == 0:
            return tag
    return CONVENTIONAL_BASELINE


def validate_release_commits(tags: list[str]) -> None:
    """Require Conventional subjects for non-merge release commits."""
    start = release_commit_start(tags)
    subjects = run(
        "git",
        "log",
        f"{start}..HEAD",
        "--no-merges",
        "--format=%s",
        capture=True,
    )
    for subject in subjects.splitlines():
        try:
            validate_commit_title(subject)
        except ValueError as exc:
            raise ValueError(f"Invalid release commit title: {subject}") from exc


def prepare_changelog(
    version: str,
    destination: Path,
    archive_dir: Path,
    promotion_from: str | None = None,
) -> None:
    """Generate and archive changelog content in a temporary workspace."""
    generated = run(
        "git-cliff",
        "--unreleased",
        "--tag",
        f"v{version}",
        "--strip",
        "header",
        capture=True,
    )
    generated_preamble, generated_sections = split_changelog(generated)
    if len(generated_sections) != 1 or generated_sections[0].label != version:
        raise ValueError(
            "git-cliff did not generate exactly one target release section"
        )

    source = PROJECT_ROOT / "CHANGELOG.md"
    _existing_preamble, existing_sections = split_changelog(
        source.read_text(encoding="utf-8")
    )
    unreleased = next(
        (section for section in existing_sections if section.label == "Unreleased"),
        None,
    )
    existing_release = next(
        (section for section in existing_sections if section.label == version),
        None,
    )
    release = generated_sections[0]
    baseline = unreleased or existing_release
    if baseline is not None:
        release = merge_unreleased(release, baseline)
    if not has_release_entries(release):
        if promotion_from is None:
            raise ValueError("Release has no changelog-visible changes")
        release = Section(
            release.label,
            f"{release.text}\n\n### Changed\n\n"
            f"- Promote {promotion_from} to the stable {version} release.",
        )
    retained = [
        section
        for section in existing_sections
        if section.label not in {"Unreleased", version}
    ]
    destination.write_text(
        format_changelog(generated_preamble, [release, *retained]),
        encoding="utf-8",
    )
    archive_changelog(version, destination, archive_dir)


def restore_files(snapshots: dict[Path, bytes | None]) -> None:
    """Restore files captured before a failed release preparation."""
    for path, content in snapshots.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def bump(version_text: str) -> None:
    """Prepare version metadata, changelog content, and archives."""
    target = parse_version(version_text)
    require_clean_tree()
    if shutil.which("git-cliff") is None:
        raise ValueError("git-cliff is required; see docs/development.md")
    current = parse_version(validate_project_version(PROJECT_ROOT))
    tags = run(
        "git",
        "tag",
        "--merged",
        "HEAD",
        "--sort=-version:refname",
        "--list",
        "v*",
        capture=True,
    ).splitlines()
    validate_release_commits(tags)
    same_unreleased_version = (
        current.text == target.text and f"v{target.text}" not in tags
    )
    if target.sort_key() <= current.sort_key() and not same_unreleased_version:
        raise ValueError(
            f"Target version {target.text} must be newer than {current.text}"
        )
    same_core = (target.major, target.minor, target.patch) == (
        current.major,
        current.minor,
        current.patch,
    )
    promotion_from = (
        current.text
        if same_core and current.prerelease and not target.prerelease
        else None
    )

    archive_root = PROJECT_ROOT / "changelogs"
    snapshot_paths = [PROJECT_ROOT / path for path in VERSION_FILES]
    snapshot_paths.extend(path for path in archive_root.glob("*.md") if path.is_file())
    snapshots = {
        path: path.read_bytes() if path.exists() else None for path in snapshot_paths
    }

    try:
        with tempfile.TemporaryDirectory(prefix="banip-release-") as temporary:
            temporary_root = Path(temporary)
            prepared_changelog = temporary_root / "CHANGELOG.md"
            prepared_archives = temporary_root / "changelogs"
            if archive_root.exists():
                shutil.copytree(archive_root, prepared_archives)
            prepare_changelog(
                target.text,
                prepared_changelog,
                prepared_archives,
                promotion_from,
            )
            if target.text != current.text:
                run("uv", "version", target.text, "--no-sync")
            (PROJECT_ROOT / "CHANGELOG.md").write_text(
                prepared_changelog.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            if prepared_archives.exists():
                archive_root.mkdir(parents=True, exist_ok=True)
                for archive in prepared_archives.glob("*.md"):
                    shutil.copy2(archive, archive_root / archive.name)
            validate_project_version(PROJECT_ROOT, target.text)
            validate_changelog_collection(
                PROJECT_ROOT / "CHANGELOG.md",
                archive_root,
                target.text,
            )
    except Exception:
        restore_files(snapshots)
        known = set(snapshots)
        for path in archive_root.glob("*.md"):
            if path not in known:
                path.unlink()
        raise


def main() -> None:
    """Parse the target version and prepare its release files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Canonical PEP 440 version, such as 2.1.0rc1.")
    args = parser.parse_args()
    try:
        bump(args.version)
    except (ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
