"""Taskrunner for check command."""

import argparse
import ipaddress as ipa

from banip.constants import IPSUM
from banip.constants import RENDERED_BLACKLIST
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    args : argparse.Namespace
        args.ip will be either IPv4 or IPv address of interest.
    """
    print()
    try:
        target = ipa.ip_address(args.ip)
    except ValueError:
        print(f"{args.ip} is not a valid IP address.")
        return

    # ----------------------------------------------------------------------

    # Load ipsum file into a dictionary.

    with open(IPSUM, "r") as f:
        ipsum: dict[AddressType, int] = {}
        for line in f:
            parts = line.strip().split()
            try:
                ip = ipa.ip_address(parts[0])
                hits = int(parts[1])
            except (ValueError, NameError):
                continue
            ipsum[ip] = hits

    # ------------------------------------------------------------------

    # Load rendered blacklist and split into networks and ip addresses

    with open(RENDERED_BLACKLIST, "r") as f:
        rendered: list[AddressType | NetworkType] = [
            token for line in f if (token := extract_ip(line.strip()))
        ]
        rendered_nets: list[NetworkType] = sorted(
            [token for token in rendered if isinstance(token, NetworkType)],
            key=lambda x: int(x.network_address),
        )
        rendered_nets_size = len(rendered_nets)
        rendered_ips: list[AddressType] = sorted(
            [token for token in rendered if isinstance(token, AddressType)],
            key=lambda x: int(x),
        )

    # ------------------------------------------------------------------

    # Check for membership.

    source = RENDERED_BLACKLIST.name
    found = False
    in_subnet = ip_in_network(
        ip=target, networks=rendered_nets, first=0, last=rendered_nets_size - 1
    )
    if target in rendered_ips or in_subnet:
        print(f"{target} found in {source}", end="")
        found = True
        if in_subnet:
            print(" (captured in subnet)")
        else:
            print()

    if target in ipsum:
        source = IPSUM.name
        msg = f"{target} found in {source} with {ipsum[target]}"
        noun = "hits" if ipsum[target] > 1 else "hit"
        print(f"{msg} {noun}.")
        found = True

    if not found:
        print(f"{target} not found.")
    print()

    return
