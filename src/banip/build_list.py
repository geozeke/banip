#! /usr/bin/env python3

"""Build a custom list of banned ips."""

import ipaddress as ipa
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path
from typing import Any

from tqdm import tqdm  # type: ignore

from banip.utilities import clear
from banip.utilities import filter_addresses
from banip.utilities import filter_networks

HOME = Path(__file__).parents[2]
COUNTRY_CODES = HOME / "data/haproxy_geo_ip.txt"
BANNED_IPS = HOME / "data/ipsum.txt"
CUSTOM_BANS = HOME / "data/custom_bans.txt"
TARGETS = HOME / "data/targets.txt"
PAD = 6


def banned_ips(args: Namespace) -> None:
    """Generate a custom list of banned IP addresses.

    Parameters
    ----------
    args : Namespace
        Command line arguments.
    """
    clear()

    # Make sure all the required files are in place

    files = [
        COUNTRY_CODES,
        BANNED_IPS,
        CUSTOM_BANS,
        TARGETS,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more info.")
            sys.exit(1)

    # Import target countries

    with open(TARGETS, "r") as f:
        countries = [
            country.upper()
            for line in f
            if (country := line.strip()) and country[0] != "#"
        ]  # fmt: skip

    # Create a list of all networks for target countries.

    print(f"Pulling networks for country codes: {countries}")
    networks_L = filter_networks(COUNTRY_CODES, countries)
    print(f"Networks pulled: {len(networks_L):,d}")

    # Now process the file of blacklisted IPs, filtering out those that have
    # less than the desired number of blacklist occurrences (hits)

    print()
    print(f"Pulling blacklisted IPs with >= {args.threshold} hits.")
    ip_L = filter_addresses(BANNED_IPS, args.threshold)
    print(f"IPs pulled: {len(ip_L):,d}")

    # This part takes the longest. Store those blacklisted IPs that are
    # hosted on the networks of target countries.

    print()
    banned_L: list[ipa.IPv4Address | ipa.IPv6Address] = []
    print(f"Building banned IP list for country codes: {countries}")
    for ip in tqdm(
        ip_L,
        desc="IPs",
        total=len(ip_L),
        colour="#bf80f2",
        unit="IPs",
    ):
        for network in networks_L:
            if ip in network:
                banned_L.append(ip)
                break
    print(f"IPs pulled: {len(banned_L):,d}")

    # Open the custom bans list and prune any IPs or networks that were
    # already discovered while building the list of banned IPs
    token: Any
    temp_ip_L: list[ipa.IPv4Address | ipa.IPv6Address] = []
    custom_net_L: list[ipa.IPv4Network | ipa.IPv6Network] = []
    with open(CUSTOM_BANS, "r") as f:
        for line in f:
            if token := line.strip():
                if "/" in token:
                    custom_net_L.append(ipa.ip_network(token))
                else:
                    temp_ip_L.append(ipa.ip_address(token))
    temp_ip_L.sort()
    custom_net_L.sort()
    banned_L.sort()
    custom_ip_L = [ip for ip in temp_ip_L if ip not in banned_L]

    # Rewrite the custom bans list with the duplicates removed.

    with open(CUSTOM_BANS, "w") as f:
        for ip in custom_ip_L:
            f.write(f"{format(ip)}\n")
        for network in custom_net_L:
            f.write(f"{format(network)}\n")

    # Write banned IPs and custom entries to the file and display
    # results.

    for ip in banned_L:
        args.outfile.write(f"{format(ip)}\n")
    now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    args.outfile.write("\n# ------------custom entries -------------\n")
    args.outfile.write(f"# Added on: {now}\n")
    args.outfile.write("# ----------------------------------------\n\n")
    for ip in custom_ip_L:
        args.outfile.write(f"{format(ip)}\n")
    for network in custom_net_L:
        args.outfile.write(f"{format(network)}\n")

    ips_found = len(banned_L)
    custom_bans = len(custom_ip_L) + len(custom_net_L)
    duplicates = len(temp_ip_L) - len(custom_ip_L)
    total_bans = ips_found + custom_bans - duplicates

    print(f"\n      Banned IPs found: {ips_found:>{PAD},d}")
    print(f"  Custom bans provided: {custom_bans:>{PAD},d}")
    print(f"    Duplicates removed: {duplicates:>{PAD},d}")
    print(f"Total banned IPs saved: {total_bans:>{PAD},d}")

    return
