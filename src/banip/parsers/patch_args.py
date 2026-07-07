"""Argument parser for the patch command."""

from argparse import FileType
from argparse import _SubParsersAction

from banip.argument_types import threshold_type

COMMAND_NAME = "patch"


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Patch the ipsum.txt file with the contents of another list of IP
    addresses. Results are deduplicated, and only new entries are added
    to ipsum.txt.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)

    msg = """
    File containing additional IP addresses to augment ipsum.txt.
    """
    parser.add_argument("newips", type=FileType("r"), help=msg)

    msg = """
    Files of additional IP addresses must be text files with an IP
    address somewhere on each line. Lines may also contain metadata or
    comments. During processing, each line is split on spaces. Use -i to
    choose which element returned by split() contains the IP address.
    The default is -1, the last element.
    """
    parser.add_argument("-i", "--index", type=int, help=msg, default=-1)

    msg = """
    Each banned IP address in ipsum.txt has a factor (from 1 to 10)
    indicating confidence that the IP address is malicious (higher is
    more confident). Use this option to set the confidence factor for
    all new IP addresses added to ipsum.txt. The default is 10.
    """
    parser.add_argument("-c", "--confidence", type=threshold_type, help=msg, default=10)

    return


if __name__ == "__main__":
    pass
