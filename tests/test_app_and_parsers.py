"""Tests for CLI entry points and parser registration."""

import argparse
import runpy
from argparse import _SubParsersAction
from pathlib import Path

import pytest

from banip import app
from banip.parsers import bots_args
from banip.parsers import build_args
from banip.parsers import check_args
from banip.parsers import database_args
from banip.parsers import patch_args
from banip.parsers import stats_args


@pytest.mark.parametrize(
    "parser_module",
    [bots_args, build_args, check_args, database_args, patch_args, stats_args],
)
def test_parser_modules_register_commands(parser_module) -> None:
    """Each parser module registers its command name."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    assert isinstance(subparsers, _SubParsersAction)
    parser_module.load_command_args(subparsers)
    assert parser_module.COMMAND_NAME in subparsers.choices


def test_command_registry_matches_parser_modules() -> None:
    """Every registered parser has one built-in command implementation."""
    parser_commands = {module.COMMAND_NAME for module in app.PARSER_MODULES}

    assert set(app.COMMAND_MODULES) == parser_commands


def test_build_outfile_is_parsed_as_a_path() -> None:
    """The build parser does not open or truncate its output path."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    build_args.load_command_args(subparsers)

    args = parser.parse_args(["build", "--outfile", "custom.txt"])

    assert args.outfile == Path("custom.txt")


def test_patch_input_is_parsed_without_opening_a_file() -> None:
    """Patch parsing accepts paths and stdin without opening resources."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    patch_args.load_command_args(subparsers)

    assert parser.parse_args(["patch", "missing.txt"]).newips == Path("missing.txt")
    assert parser.parse_args(["patch", "-"]).newips == Path("-")


def test_check_parses_zero_or_more_ip_addresses() -> None:
    """Check accepts interactive, single-address, and batch invocations."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    check_args.load_command_args(subparsers)

    interactive = parser.parse_args(["check"])
    batch = parser.parse_args(["check", "192.0.2.1", "2001:db8::1"])

    assert interactive.ip_addresses == []
    assert [str(address) for address in batch.ip_addresses] == [
        "192.0.2.1",
        "2001:db8::1",
    ]


def test_check_rejects_invalid_ip_address() -> None:
    """Check delegates invalid command-line addresses to argparse."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    check_args.load_command_args(subparsers)

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["check", "invalid"])

    assert exc_info.value.code == 2


def test_main_ignores_and_preserves_legacy_plugin_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Legacy plugin files are untouched and no longer become commands."""
    parser_dir = tmp_path / "plugins" / "parsers"
    code_dir = tmp_path / "plugins" / "code"
    parser_dir.mkdir(parents=True)
    code_dir.mkdir(parents=True)
    (parser_dir / "custom_args.py").write_text(
        "def load_command_args(subparsers):\n    subparsers.add_parser(name='custom')\n"
    )
    (code_dir / "custom.py").write_text(
        "def task_runner(args):\n    print('legacy plugin ran')\n"
    )
    monkeypatch.setattr("sys.argv", ["banip", "custom"])

    with pytest.raises(SystemExit) as exc_info:
        app.main()

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "invalid choice" in captured.err
    assert "legacy plugin ran" not in captured.out
    assert (parser_dir / "custom_args.py").is_file()
    assert (code_dir / "custom.py").is_file()


def test_module_entry_point_delegates_to_app_main(monkeypatch) -> None:
    """``python -m banip`` delegates to ``banip.app.main``."""
    monkeypatch.setattr(app, "main", lambda: 7)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("banip.__main__", run_name="__main__")

    assert exc_info.value.code == 7


def test_help_works_before_local_setup(monkeypatch, capsys) -> None:
    """Help output does not require the local ~/.banip setup."""
    monkeypatch.setattr(app, "__version__", "test-version")
    monkeypatch.setattr(app, "check_setup", lambda: False)
    monkeypatch.setattr("sys.argv", ["__main__.py", "-h"])

    with pytest.raises(SystemExit) as exc_info:
        app.main()

    output = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "usage: banip" in output
    assert "Version: test-version" in output


def test_command_checks_local_setup_after_parsing(monkeypatch, capsys) -> None:
    """Real commands still require the local ~/.banip setup."""
    called = False

    def fail_setup() -> bool:
        nonlocal called
        called = True
        return False

    monkeypatch.setattr("sys.argv", ["banip", "build"])
    monkeypatch.setattr(app, "check_setup", fail_setup)

    app.main()

    assert called
    assert "not configured correctly" not in capsys.readouterr().err
