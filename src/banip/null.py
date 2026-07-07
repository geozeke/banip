"""Task runner for no command.

This is the default command. It reminds the user how to use the program
and then exits.
"""

import argparse


def task_runner(args: argparse.Namespace) -> None:
    """Print a reminder message and exit."""
    print("Run 'banip -h' for help.")
    return
