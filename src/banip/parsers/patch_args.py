"""Argument parser for build command."""

from argparse import FileType
from argparse import _SubParsersAction

from banip.argument_types import threshold_type

COMMAND_NAME = "patch"


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Patch the ipsum.txt file with the contents of another list of IP
    addresses. Results will be de-duplicated, and only new entries will
    be added to ipsum.txt
    """
    parser = sp.add_parser(name=COMMAND_NAME, help=msg, description=msg)

    msg = """
    File containing additional IP addresses to augment ipsum.txt.
    """
    parser.add_argument("newips", type=FileType("r"), help=msg)

    msg = """
    Files of additional IP addesses must text files, where an IP address
    is located somewhere on each line. In addition to the IP address,
    there may be metadata or other items (e.g. comments) on each line.
    During processing, each line will be read, then split on space. Use
    the -i option to define which element in the list returned from
    split() to use to capture the IP address. The default is -1 (the
    last one).
    """
    parser.add_argument("-i", "--index", type=int, help=msg, default=-1)

    msg = """
    Each banned IP address in ipsum.txt has a factor (from 1 to 10)
    indicating a level of confidence that the IP address is a malicious
    actor (higher is more confident). Use this option to set the
    confidence factor of all the new IPs that you are adding to
    ipsum.txt. The default threshold used is 10.
    """
    parser.add_argument("-c", "--confidence", type=threshold_type, help=msg, default=10)

    return


if __name__ == "__main__":
    pass
