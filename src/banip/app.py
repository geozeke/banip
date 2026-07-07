#!/usr/bin/env python3

"""Entry point for banip."""

import argparse
import importlib
import importlib.util
import sys
from importlib.metadata import version
from pathlib import Path
from types import ModuleType

from banip.constants import APP_NAME
from banip.constants import ARG_PARSERS_BASE
from banip.constants import CUSTOM_CODE
from banip.constants import CUSTOM_PARSERS
from banip.constants import DATA
from banip.utilities import print_docstring

__version__ = version("banip")

# ======================================================================


def check_setup() -> bool:
    """Check whether the local environment is configured.

    Returns
    -------
    bool
        True if the required directories exist; otherwise False.
    """
    proper_setup = (
        CUSTOM_PARSERS.exists()
        and CUSTOM_CODE.exists()
        and (DATA / "geolite").exists()
    )  # fmt: off
    if not proper_setup:
        msg = """
        The local environment is not configured correctly. Make sure
        the following structure exists in your home directory:

        .banip
        ├── geolite
        └── plugins
            ├── code
            └── parsers
        """
        print_docstring(msg=msg)
        return False
    return True


# ======================================================================


def load_custom_module(mod_name: str, location: Path) -> ModuleType:
    """Load a custom module.

    Parameters
    ----------
    mod_name : str
        The name of the module to load.
    location : Path
        The absolute path to the Python code for the module.

    Returns
    -------
    ModuleType
        The loaded module.
    """
    mod_path = f"{location}/{mod_name}.py"
    if spec := importlib.util.spec_from_file_location(mod_name, mod_path):
        if (module := importlib.util.module_from_spec(spec)) and spec.loader:
            spec.loader.exec_module(module)
    return module


# ======================================================================


def collect_parsers(start: Path) -> list[str]:
    """Collect the module names of all argument parsers to import.

    Parameters
    ----------
    start : Path
        The directory where parser collection starts.

    Returns
    -------
    list[str]
        Argument parser module names.
    """
    parser_names: list[str] = []
    if not start.exists():
        return parser_names
    for p in start.iterdir():
        if p.is_file() and p.name.endswith(".py") and p.name != "__init__.py":
            if "plugins" in str(p):
                prefix = "plugins.parsers"
            else:
                prefix = "parsers"
            parser_names.append(f"{prefix}.{p.stem}")
    return parser_names


# ======================================================================


def main() -> int:
    """Parse user input and run the requested command."""
    msg = """
    Generate and query IP blacklists for use with proxy servers such as
    HAProxy. See the README at https://github.com/geozeke/banip for
    setup instructions.
    """
    epi = f"Version: {__version__}"
    parser = argparse.ArgumentParser(prog=APP_NAME, description=msg, epilog=epi)
    parser.add_argument(
        "-v", "--version", action="version", version=f"{APP_NAME} {__version__}"
    )
    msg = "For help on any command below, run: banip {command} -h."
    subparsers = parser.add_subparsers(title="commands", dest="cmd", description=msg)

    # Dynamically load argument subparsers and process command line
    # arguments.

    parser_names: list[str] = []
    mod: ModuleType | None = None
    parser_names = collect_parsers(ARG_PARSERS_BASE)
    parser_names += collect_parsers(CUSTOM_PARSERS)
    parser_names = sorted(parser_names, key=lambda x: x.split(".")[-1])
    for p_name in parser_names:
        if "plugins" not in p_name:
            parser_code = importlib.import_module(f"banip.{p_name}")
        else:
            parser_code = load_custom_module(
                p_name.split(".")[-1], location=CUSTOM_PARSERS
            )
        parser_code.load_command_args(subparsers)
    args = parser.parse_args()

    # Make sure the local setup is complete after parsing so help and
    # version output work in a fresh environment.
    if args.cmd and not check_setup():
        return 1

    # Run the selected command. Python's argparse module guarantees that
    # we'll get either: (1) a valid command (base or custom) or (2) no
    # command at all. Given that, we can determine whether the entered
    # command is built in or custom based on its companion in the list of
    # argument parser names. We then adjust the prefix based on that.

    if args.cmd:
        try:
            if f"parsers.{args.cmd}_args" in parser_names:
                mod_name = f"{APP_NAME}.{args.cmd}"
                mod = importlib.import_module(mod_name)
            else:
                mod = load_custom_module(args.cmd, location=CUSTOM_CODE)
        except (ModuleNotFoundError, FileNotFoundError):
            msg = f"""
            Code for a custom command must have the same filename as the
            command itself. Make sure you have a Python file called
            \"{args.cmd}.py\" in: {CUSTOM_CODE}
            """
            print("\n".join([line.strip() for line in msg.split("\n")]))
            sys.exit(1)
    else:
        mod = importlib.import_module(f"{APP_NAME}.null")

    mod.task_runner(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
