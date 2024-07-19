#!/usr/bin/env python3

"""Entry point for banip."""

import argparse
import importlib
import sys
from pathlib import Path
from types import ModuleType

from banip.constants import APPLICATION_NAME
from banip.constants import ARG_PARSERS_BASE
from banip.constants import ARG_PARSERS_CUSTOM
from banip.constants import CUSTOM_CODE
from banip.utilities import wrap_tight

# ======================================================================


def collect_parsers(start: Path) -> list[str]:
    """Collect the module names of all argument parsers to import.

    Parameters
    ----------
    start : Path
        This the starting point (directory) for collection.

    Returns
    -------
    list[str]
        A list of argument parser module names.
    """
    parser_names: list[str] = []
    for p in start.iterdir():
        if p.is_file() and p.name != "__init__.py":
            if "plugins" in str(p):
                prefix = "plugins.parsers"
            else:
                prefix = "parsers"
            parser_names.append(f"{prefix}.{p.stem}")
    return parser_names


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

    # Dynamically load argument subparsers and process command line
    # arguments.

    parser_names: list[str] = []
    mod: ModuleType | None = None
    parser_names = collect_parsers(ARG_PARSERS_BASE)
    parser_names += collect_parsers(ARG_PARSERS_CUSTOM)
    for p_name in parser_names:
        parser_code = importlib.import_module(p_name)
        parser_code.load_command_args(subparsers)
    args = parser.parse_args()

    # Run the selected command. Python's argparse module guarantees that
    # we'll get either: (1) a valid command (base or custom) or (2) no
    # command at all (args.cmd == None). Given that, we can easily
    # determine if the entered command is base or custom, based on its
    # companion in the list of argument parser names. We then adjust the
    # prefix based on that.

    if args.cmd:
        if f"parsers.{args.cmd}_args" in parser_names:
            prefix = f"{APPLICATION_NAME}"
        else:
            prefix = "plugins.code"
        try:
            mod = importlib.import_module(f"{prefix}.{args.cmd}")
        except ModuleNotFoundError:
            msg = f"""Code for a custom command must have the same
            filename as the command itself. Make sure you have a program
            file called \"{args.cmd}.py\" in {CUSTOM_CODE}/"""
            print(wrap_tight(msg))
            sys.exit(1)
    else:
        mod = importlib.import_module(f"{APPLICATION_NAME}.null")
    mod.task_runner(args)

    return


if __name__ == "__main__":
    main()
