"""Taskrunner for check command."""

import argparse

from banip.constants import IPSUM_IPS
from banip.constants import RENDERED_BLACKLIST
from banip.utilities import extract_ip
from banip.utilities import load_dictionary


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    args : argparse.Namespace
        args.ip will be either IPv4 or IPv address of interest.
    """
    print()
    if not (target := extract_ip(args.ip)):
        print(f"{args.ip} is not a valid IP address.")
        return

    # Create a dictionary to hold lists of the file contents. These are
    # the keys that will be used:

    # V4A: IPv4 Addresses.
    # V6A: IPv6 Addresses.
    # V4N: IPv4 Subnets.
    # V6N: IPv6 Subnets.

    source = RENDERED_BLACKLIST.name
    msg = ""
    if not (D := load_dictionary(RENDERED_BLACKLIST)):
        print(f"Source file: {source} not found.")
        return
    if not (found := target in (D["V4A"] + D["V6A"])):
        found = any([net
                    for net in (D["V4N"] + D["V6N"])
                    if target in net])  # fmt: skip
        msg = " (captured in subnet)"
    if found:
        print(f"{target} found in {source}{msg}")

    if IPSUM_IPS.exists():
        source = IPSUM_IPS.name
        with open(IPSUM_IPS, "r") as f:
            for line in f:
                if str(target) in line:
                    hitcount = int(line.split()[1])
                    msg = f"{args.ip} found in {source} with {hitcount}"
                    noun = "hits" if hitcount > 1 else "hit"
                    print(f"{msg} {noun}.")
                    found = True
                    break

    if not found:
        print(f"{target} not found.")

    print()
    return
