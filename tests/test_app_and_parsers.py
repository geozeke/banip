"""Tests for CLI entry points and parser registration."""

import argparse
import runpy
from argparse import _SubParsersAction
from pathlib import Path

import pytest

from banip import app
from banip.parsers import build_args
from banip.parsers import check_args
from banip.parsers import patch_args
from banip.parsers import stats_args


@pytest.mark.parametrize(
    "parser_module",
    [build_args, check_args, patch_args, stats_args],
)
def test_parser_modules_register_commands(parser_module) -> None:
    """Each parser module registers its command name."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd")
    assert isinstance(subparsers, _SubParsersAction)
    parser_module.load_command_args(subparsers)
    assert parser_module.COMMAND_NAME in subparsers.choices


def test_collect_parsers_excludes_init(tmp_path: Path) -> None:
    """Parser collection skips package initializers."""
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "foo.py").write_text("")
    (tmp_path / "bar.py").write_text("")

    assert sorted(app.collect_parsers(tmp_path)) == ["parsers.bar", "parsers.foo"]


def test_collect_parsers_returns_empty_list_for_missing_directory(
    tmp_path: Path,
) -> None:
    """Missing parser directories do not block base help output."""
    assert app.collect_parsers(tmp_path / "missing") == []


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
