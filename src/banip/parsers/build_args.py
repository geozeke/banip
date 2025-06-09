"""Argument parser for build command."""

from argparse import FileType
from argparse import _SubParsersAction

from banip.argument_types import compact_type
from banip.argument_types import threshold_type

COMMAND_NAME = "build"


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Create a list of banned (blacklisted) client IP addresses to be used
    with a proxy server (like HAProxy) to block network access from
    those clients.
    """
    parser = sp.add_parser(name=COMMAND_NAME, help=msg, description=msg)

    msg = """
    Output file that will contain the generated list of blacklisted IP
    addresses. If not provided, results will be saved to
    ./data/ip_blacklist.txt
    """
    parser.add_argument("-o", "--outfile", type=FileType("w"), help=msg)

    msg = """
    Each banned IP address in the source database has a factor (from 1
    to 10) indicating a level of confidence that the IP address is a
    malicious actor (higher is more confident). The default threshold
    used is 3. Anything less than that may result in false positives,
    but you may choose any threshold from 1 to 10. If you find you're
    getting false positives, just re-run banip with a higher threshold.
    """
    parser.add_argument("-t", "--threshold", type=threshold_type, help=msg, default=3)

    msg = """
    The ipsum.txt file contains many entries which all reside in the
    same Class-C subnet (i.e. /24). Compacting those entries into a
    single /24 subnet can significantly reduce the size of the
    blacklist. COMPACT is an integer from 1 to 255 indicating how many
    IP addresses from the single /24 subnet need to be present before
    they're compacted. Smaller numbers create a smaller (more compact)
    blacklist. NOTE: compacting the blacklist can result in
    overblocking. For example, by compacting several IP addresses into
    something like 45.78.4.0/24, you may block some benign IPs within
    the same range that were not explicitly in your blacklist.
    """
    parser.add_argument("-c", "--compact", type=compact_type, help=msg, default=0)

    return


if __name__ == "__main__":
    pass
