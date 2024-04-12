"""Taskrunner for check command."""

import argparse
import ipaddress as ipa

from banip.constants import BANNED_IPS
from banip.constants import RENDERED_BLACKLIST


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    args : argparse.Namespace
        args.ip will be either IPv4 or IPv address of interest.
    """
    try:
        ipa.ip_address(args.ip)
    except ValueError:
        print(f"{args.ip} is not a valid IP address.")
        return

    print()
    found = False
    if RENDERED_BLACKLIST.exists():
        with open(RENDERED_BLACKLIST, "r") as f:
            for line in f:
                if args.ip in line:
                    source = RENDERED_BLACKLIST.name
                    print(f"{args.ip} found in {source}")
                    found = True
                    break

    if BANNED_IPS.exists():
        source = BANNED_IPS.name
        with open(BANNED_IPS, "r") as f:
            for line in f:
                if args.ip in line:
                    hitcount = int(line.split()[1])
                    msg = f"{args.ip} found in {source} with {hitcount}"
                    noun = "hits" if hitcount > 1 else "hit"
                    print(f"{msg} {noun}.")
                    found = True
                    break

    if not found:
        print(f"{args.ip} not found.")

    return
