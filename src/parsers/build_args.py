"""Argument parser for build command."""

import argparse
from argparse import _SubParsersAction

COMMAND_NAME = "build"


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Create a list of banned (blacklisted) client IP addresses to be used
    with a proxy server (like HAProxy) to block network access from
    those clients.
    """
    parser = sp.add_parser(
        name=COMMAND_NAME,
        help=msg,
        description=msg,
    )

    msg = """
    Output file that will contain the generated list of blacklisted IP
    addresses. If not provided, results will be saved to
    ./data/ip_blacklist.txt
    """
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        help=msg,
    )

    msg = """
    Each banned IP address in the source database has a factor (from 1
    to 10) indicating a level of confidence that the IP address is a
    malicious actor (higher is more confident). The default threshold
    used is 3. Anything less than that may result in false positives,
    but you may choose any threshold from 1 to 10. If you find you're
    getting false positives, just re-run banip with a higher threshold.
    """
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        help=msg,
        default=3,
    )

    return


if __name__ == "__main__":
    pass
