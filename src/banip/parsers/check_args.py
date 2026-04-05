"""Argument parser for check command."""

from argparse import _SubParsersAction

COMMAND_NAME = "check"


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Check to see if a single IP address is found in the data generated
    from running \"banip build\". For example, if the IP resides in a
    country that is not part of targets.txt then it could show up in
    ipsum.txt, but will not show up in the rendered blacklist. The
    rendered blacklist only reflects those countries that are in
    targets.txt
    """
    sp.add_parser(name=COMMAND_NAME, description=msg)

    return
