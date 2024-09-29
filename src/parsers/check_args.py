"""Argument parser for check command."""

from argparse import _SubParsersAction

COMMAND_NAME = "check"


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Check to see if a single IP address is found in the blacklist.
    """
    parser = sp.add_parser(
        name=COMMAND_NAME,
        help=msg,
        description=msg,
    )

    msg = """
    This is the IPv4 or IPv6 address you're interested in. After you run
    banip for the first time, you can use the "check" command to see if
    a single IP address is found in the blacklist. Making subsequent
    runs of banip to generate new blacklists will use the updated
    information for future IP checking.
    """
    parser.add_argument(
        "ip",
        type=str,
        help=msg,
    )

    return
