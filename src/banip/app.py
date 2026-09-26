#!/usr/bin/env python3

"""Entry point for banip."""

import argparse
from importlib.metadata import version
from types import ModuleType

from banip import bots as bots_command
from banip import build as build_command
from banip import check as check_command
from banip import database as database_command
from banip import null as null_command
from banip import patch as patch_command
from banip import stats as stats_command
from banip.constants import APP_NAME
from banip.constants import DATA
from banip.parsers import bots_args
from banip.parsers import build_args
from banip.parsers import check_args
from banip.parsers import database_args
from banip.parsers import patch_args
from banip.parsers import stats_args
from banip.utilities import print_docstring

__version__ = version("banip")

PARSER_MODULES: tuple[ModuleType, ...] = (
    bots_args,
    build_args,
    check_args,
    database_args,
    patch_args,
    stats_args,
)
COMMAND_MODULES: dict[str, ModuleType] = {
    bots_args.COMMAND_NAME: bots_command,
    build_args.COMMAND_NAME: build_command,
    check_args.COMMAND_NAME: check_command,
    database_args.COMMAND_NAME: database_command,
    patch_args.COMMAND_NAME: patch_command,
    stats_args.COMMAND_NAME: stats_command,
}


def check_setup() -> bool:
    """Check whether the local environment is configured.

    Returns
    -------
    bool
        True if the required directories exist; otherwise False.

    """
    proper_setup = (DATA / "geolite").exists()
    if not proper_setup:
        msg = """
        The local environment is not configured correctly. Make sure
        the following structure exists in your home directory:

        .banip
        └── geolite
        """
        print_docstring(msg=msg)
        return False
    return True


def requires_setup(args: argparse.Namespace) -> bool:
    """Return whether a command requires initialized local data paths.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.

    Returns
    -------
    bool
        True when setup should be checked before dispatch.

    """
    return not (args.cmd == "database" and args.action == "init")


def main() -> int:
    """Parse user input and run the requested command."""
    msg = """
    Generate and query IP blocklists for use with proxy servers such as
    HAProxy. See https://geozeke.github.io/banip/ for
    setup instructions.
    """
    epi = f"Version: {__version__}"
    parser = argparse.ArgumentParser(prog=APP_NAME, description=msg, epilog=epi)
    parser.add_argument(
        "-v", "--version", action="version", version=f"{APP_NAME} {__version__}"
    )
    msg = "For help on any command below, run: banip {command} -h."
    subparsers = parser.add_subparsers(title="commands", dest="cmd", description=msg)

    for parser_module in PARSER_MODULES:
        parser_module.load_command_args(subparsers)
    args = parser.parse_args()

    # Make sure the local setup is complete after parsing so help and
    # version output work in a fresh environment.
    if args.cmd and requires_setup(args) and not check_setup():
        return 1

    if args.cmd:
        command_module = COMMAND_MODULES[args.cmd]
    else:
        command_module = null_command

    command_module.task_runner(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
