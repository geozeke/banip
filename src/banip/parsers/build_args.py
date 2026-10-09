"""Argument parser for build command."""

from __future__ import annotations

from argparse import ArgumentParser
from argparse import _SubParsersAction
from pathlib import Path

from banip.argument_types import compact_type
from banip.argument_types import threshold_type

COMMAND_NAME = "build"


# ======================================================================


def load_command_args(sp: _SubParsersAction[ArgumentParser]) -> None:
    """Assemble the argument parser."""
    msg = """
    Create a list of blocked client IP addresses and networks for use
    with proxies and firewalls, such as HAProxy.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)

    msg = """
    Output file for the generated IP blocklist. If not provided, results
    are saved to ~/.banip/ip_blocklist.txt. When an alternate path is
    used, the canonical copy is also refreshed for other banip commands.
    """
    parser.add_argument("-o", "--outfile", type=Path, help=msg)

    msg = """
    Each IP address in the ipsum feed has a confidence score from 1 to
    10 (higher is more confident). Include addresses at or above this
    score. The default is 3. Lower values may produce false positives.
    """
    parser.add_argument("-t", "--threshold", type=threshold_type, help=msg, default=3)

    msg = """
    Compact multiple IP addresses from the same /24 subnet into one
    subnet entry. COMPACT is an integer from 1 to 255 that defines how
    many IP addresses must be present in a /24 before they are
    compacted. The default 0 disables compaction; enabled values range
    from 1 to 255. Smaller values create a smaller blocklist. Compaction
    can cause overblocking; for example, compacting several IP addresses
    into 45.78.4.0/24 may block benign addresses in that range.
    """
    parser.add_argument("-c", "--compact", type=compact_type, help=msg, default=0)

    msg = """
    Do not load managed crawler and bot ranges from ~/.banip/botdata.json
    during this build.
    """
    parser.add_argument("--no-bots", action="store_true", help=msg)

    return


if __name__ == "__main__":
    pass
