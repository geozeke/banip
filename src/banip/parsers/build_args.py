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
    Create a list of banned client IP addresses for use with a proxy
    server, such as HAProxy.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)

    msg = """
    Output file for the generated IP blacklist. If not provided, results
    are saved to ~/.banip/ip_blacklist.txt.
    """
    parser.add_argument("-o", "--outfile", type=FileType("w"), help=msg)

    msg = """
    Each banned IP address in the source database has a factor (from 1
    to 10) indicating confidence that the IP address is malicious
    (higher is more confident). The default threshold is 3. Lower values
    may produce false positives. If that happens, rerun banip with a
    higher threshold.
    """
    parser.add_argument("-t", "--threshold", type=threshold_type, help=msg, default=3)

    msg = """
    Compact multiple IP addresses from the same /24 subnet into one
    subnet entry. COMPACT is an integer from 1 to 255 that defines how
    many IP addresses must be present in a /24 before they are
    compacted. Smaller values create a smaller blacklist. Compaction can
    cause overblocking; for example, compacting several IP addresses
    into 45.78.4.0/24 may block benign addresses in that range.
    """
    parser.add_argument("-c", "--compact", type=compact_type, help=msg, default=0)

    return


if __name__ == "__main__":
    pass
