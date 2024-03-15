"""Taskrunner for no command.

This will be the default command, which simply allows the program to
exit.
"""

import argparse


def task_runner(args: argparse.Namespace) -> None:
    """Do nothing."""
    return
