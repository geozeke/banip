#!/usr/bin/env python3

"""Docstring."""

import argparse

from banip.build_list import banned_ips


def main() -> None:
    """Do this."""
    msg = """This program will create a list of banned (blacklisted)
    ipaddresses to be used with a proxy server (like HAProxy) to block
    network access. Please review the README file at
    https://github.com/geozeke/ubuntu for detailed instructions."""

    epi = "Version: 0.1.0"

    parser = argparse.ArgumentParser(description=msg, epilog=epi)

    msg = """The file that will contain the generated list of banned
    ip addresses"""
    parser.add_argument("outfile", type=argparse.FileType("w"), help=msg)

    msg = """Each banned ip address in the source database has a factor
    (from 1 to 10) indicating a level of certainty that the ip address is a
    malicious actor. The default threshold used is 3. Anything
    less than that may result in false positives and increases the time
    required to generate the list. You may choose any threshold from 1
    to 10, but I recommend not going lower than 3."""
    parser.add_argument(
        "-t",
        "--threshold",
        type=int,
        help=msg,
        default=3,
    )

    args = parser.parse_args()
    banned_ips(args)
    args.outfile.close()
    return


if __name__ == "__main__":
    main()
