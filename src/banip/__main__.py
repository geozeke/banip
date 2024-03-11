#!/usr/bin/env python3

"""Entry point for banip."""

import argparse

from argparse_formatter import ParagraphFormatter  # type:ignore

from banip.build_list import banned_ips
from banip.contants import RENDERED_BLACKLIST
from banip.utilities import check_ip


def main() -> None:
    """Get user input and build the list of banned IP addresses."""
    msg = """banip will create a list of banned (blacklisted)
    client IP addresses to be used with a proxy server (like HAProxy) to
    block network access from those clients. Alternatively, you can use
    banip to check to see if a single IP address is found in the
    blacklist.

    Please review the README file at this link for detailed instructions
    on setting up banip: https://github.com/geozeke/ubuntu"""

    epi = "Version: 0.1.0"

    parser = argparse.ArgumentParser(
        description=msg,
        epilog=epi,
        formatter_class=ParagraphFormatter,
    )

    subparsers = parser.add_subparsers(title="Sub-commands")
    msg = """Alternatively, you can use banip to check to see if a
    single IP address is found in the blacklist. Run banip check -h for
    more."""
    subparser_check = subparsers.add_parser(name="check", help=msg)

    msg = """Output file that will contain the generated list of banned
    IP addresses. If not provided, results will be saved to
    ./data/ip_blacklist.txt"""
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        help=msg,
    )

    msg = """Each banned IP address in the source database has a factor
    (from 1 to 10) indicating a level of confidence that the IP address
    is a malicious actor (higher is more confident). The default
    threshold used is 3. Anything less than that may result in false
    positives, but you may choose any threshold from 1 to 10. If you
    find you are getting false positives, just re-run banip with a
    higher threshold."""
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        help=msg,
        default=3,
    )

    msg = """This is the IPv4 or IPv6 address you're interested in.
    After you run banip for the first time, you can use the "check"
    subcommand to see if a single IP address is found in the blacklist.
    Making subsequent runs of banip to generate new blacklists will use
    the updated information for future IP checking."""
    subparser_check.add_argument(
        "ip",
        type=str,
        help=msg,
    )

    args = parser.parse_args()
    if hasattr(args, "ip"):
        check_ip(args.ip)
    else:
        if not args.outfile:
            args.outfile = open(RENDERED_BLACKLIST, "w")
        banned_ips(args)
    return


if __name__ == "__main__":
    main()
