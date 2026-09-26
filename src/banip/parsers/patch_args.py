"""Argument parser for the patch command."""

from argparse import _SubParsersAction
from pathlib import Path

from banip.argument_types import threshold_type

COMMAND_NAME = "patch"


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Patch the ipsum.txt file with the contents of another list of IP
    addresses. Results are deduplicated. Existing addresses retain their
    confidence unless the requested confidence is higher.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)

    msg = """
    UTF-8 file containing additional IP addresses to augment ipsum.txt.
    Use - to read from standard input.
    """
    parser.add_argument("newips", type=Path, help=msg)

    msg = """
    Files of additional IP addresses must be text files with an IP
    address somewhere on each line. Lines may also contain metadata or
    comments. During processing, each line is split on whitespace. Use
    -i to choose which element contains the IP address. The default is
    -1, the last element.
    """
    parser.add_argument("-i", "--index", type=int, help=msg, default=-1)

    msg = """
    Each IP address in ipsum.txt has a confidence score from 1 to 10
    (higher is more confident). Set the score for new addresses and
    raise existing lower scores to this value. The default is 10.
    """
    parser.add_argument("-c", "--confidence", type=threshold_type, help=msg, default=10)

    return


if __name__ == "__main__":
    pass
