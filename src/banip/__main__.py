#!/usr/bin/env python3

"""Entry point for banip."""

import argparse
import importlib
from pathlib import Path
from types import ModuleType

from banip.constants import ARG_PARSERS_BASE
from banip.constants import ARG_PARSERS_CUSTOM
from banip.constants import CUSTOM_CODE
from banip.utilities import wrap_tight

# ======================================================================


def collect_parsers(start: Path) -> list[str]:
    """Collect the filenames of all argument parsers to import.

    Parameters
    ----------
    start : Path
        This the starting point (directory) for collection.

    Returns
    -------
    list[str]
        A list of argument parser filenames (complete paths).
    """
    module_names: list[str] = []
    for p in start.iterdir():
        if p.is_file() and p.name != "__init__.py":
            if "plugins" in str(p):
                prefix = "plugins.parsers"
            else:
                prefix = "parsers"
            module_names.append(f"{prefix}.{p.stem}")
    return module_names


# ======================================================================


def load_custom_module(cmd: str) -> ModuleType | None:
    """Given the name of a command, return the associated module.

    By design, the code associated with a given command must have the
    same name as the command itself. This function loads the module, and
    returns a pointer to it.

    Parameters
    ----------
    cmd : str
        The name of a banip command

    Returns
    -------
    ModuleType | None
        This will be a pointer to the imported python module.
    """
    for p in CUSTOM_CODE.iterdir():
        if p.is_file():
            if p.stem == cmd:
                return importlib.import_module(f"plugins.code.{p.stem}")
    return None


# ======================================================================


def main() -> None:
    """Get user input and build the list of banned IP addresses."""
    msg = """Generate and query IP blacklists for use with proxy servers
    (like HAProxy). For help on any command, run: "banip {command} -h".
    Please review the README file at https://github.com/geozeke/banip
    for detailed instructions on setting up banip."""
    epi = "Version: 1.0.0"
    parser = argparse.ArgumentParser(
        description=msg,
        epilog=epi,
    )
    subparsers = parser.add_subparsers(title="commands", dest="cmd")

    # Dynamically load argument subparsers.

    parser_names: list[str] = []
    mod: ModuleType | None = None
    parser_names = collect_parsers(ARG_PARSERS_BASE)
    parser_names += collect_parsers(ARG_PARSERS_CUSTOM)
    for p_name in parser_names:
        parser_code = importlib.import_module(p_name)
        parser_code.load_command_args(subparsers)

    args = parser.parse_args()
    match (args.cmd):
        case "build":
            mod = importlib.import_module("banip.build")
        case "check":
            mod = importlib.import_module("banip.check")
        case _:
            if args.cmd:
                if not (mod := load_custom_module(args.cmd)):
                    msg = f"""Code for a given command must have the
                    same name as the command itself. Make sure you have
                    a program file called \"{args.cmd}.py\" in
                    {CUSTOM_CODE}/"""
                    print(wrap_tight(msg))
                    mod = importlib.import_module("banip.null")
            else:
                mod = importlib.import_module("banip.null")
    mod.task_runner(args)

    return


if __name__ == "__main__":
    main()
