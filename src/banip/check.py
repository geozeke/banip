"""Taskrunner for check command."""

import argparse
import ipaddress as ipa
from pathlib import Path
from typing import Any

from banip.constants import IPSUM_IPS
from banip.constants import RENDERED_BLACKLIST


def load_dictionary(
    target_file: str | Path,
    D: dict[str, list[Any]],
) -> None:
    """Load dictionary.

    This will process the given file and load the given dictionary with
    individual lists of: IPv4Addresses, IPv6Addresses, IPv4Networks,
    IPv6Networks

    Parameters
    ----------
    target_file : str | Path
        File to be processed.
    D : dict[str, list[Any]]
        Dictionary of lists.
    """
    token: Any = None
    with open(target_file, "r") as f:
        for line in f:

            clean_line = line.strip()
            try:
                if "/" in clean_line:
                    token = ipa.ip_network(clean_line)
                else:
                    token = ipa.ip_address(clean_line)
            except ValueError:
                continue

            if type(token) is ipa.IPv4Address:
                D["V4A"].append(token)
            elif type(token) is ipa.IPv6Address:
                D["V6A"].append(token)
            elif type(token) is ipa.IPv4Network:
                D["V4N"].append(token)
            else:
                D["V6N"].append(token)

    return


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    args : argparse.Namespace
        args.ip will be either IPv4 or IPv address of interest.
    """
    try:
        target: Any = ipa.ip_address(args.ip)
    except ValueError:
        print(f"{args.ip} is not a valid IP address.")
        return

    print()

    # Create a dictionary to hold lists of the file contents. These are
    # the keys that will be used:

    # V4A: IPv4 Addresses.
    # V6A: IPv6 Addresses.
    # V4N: IPv4 Subnets.
    # V6N: IPv6 Subnets.

    # It's not strictly necessary to create four lists (could just use
    # two - ips and subnets), but having the lists compartmentalized
    # like this might be useful in the future.

    D: dict[str, list[Any]] = {
        "V4A": [],
        "V6A": [],
        "V4N": [],
        "V6N": [],
    }

    if RENDERED_BLACKLIST.exists():
        source = RENDERED_BLACKLIST.name
        msg = ""
        load_dictionary(RENDERED_BLACKLIST, D)
        found = target in (D["V4A"] + D["V6A"])
        if not found:
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
        print(f"{args.ip} not found.")

    return
