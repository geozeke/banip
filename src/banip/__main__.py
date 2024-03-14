#!/usr/bin/env python3

"""Entry point for banip."""

import argparse
import importlib
from pathlib import Path
from types import ModuleType

from banip.constants import ARG_PARSERS_BASE
from banip.constants import CUSTOM_ARG_PARSERS
from banip.constants import CUSTOM_CODE
from banip.utilities import wrap_tight

# ======================================================================


def collect_modules(start: Path) -> list[str]:
    """Collect the names of all modules to import.

    Parameters
    ----------
    start : Path
        This the starting point (directory) for collection.

    Returns
    -------
    list[str]
        A list of module names.
    """
    module_names: list[str] = []
    for p in start.iterdir():
        if p.is_file() and p.name != "__init__.py":
            if "plugins" in str(p):
                prefix = "plugins.argument_parsers"
            else:
                prefix = "argument_parsers"
            module_names.append(f"{prefix}.{p.stem}")
    return module_names


# ======================================================================


def load_custom_module(cmd: str) -> ModuleType | None:
    """Given the name of a command, return the associated module.

    By design, the code associated with a given command must have the
    same name as the command itself.

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
    Please review the README file at https://github.com/geozeke/ubuntu
    for detailed instructions on setting up banip."""
    epi = "Version: 1.0.0"
    parser = argparse.ArgumentParser(
        description=msg,
        epilog=epi,
    )
    subparsers = parser.add_subparsers(title="commands", dest="cmd")

    # Dynamically load argument subparsers.

    module_names: list[str] = []
    mod: ModuleType | None = None
    module_names = collect_modules(ARG_PARSERS_BASE)
    module_names += collect_modules(CUSTOM_ARG_PARSERS)
    for mod_name in module_names:
        mod = importlib.import_module(mod_name)
        mod.load_command_args(subparsers)

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
