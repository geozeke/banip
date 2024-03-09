#! /usr/bin/env python3

"""Build a custom list of banned ips."""

import ipaddress as ipa
import sys
from argparse import Namespace
from datetime import datetime as dt
from typing import Any

from tqdm import tqdm  # type: ignore

from banip.contants import BANNED_IPS
from banip.contants import COUNTRY_CODES
from banip.contants import CUSTOM_BANS
from banip.contants import GEOLITE_4
from banip.contants import GEOLITE_6
from banip.contants import GEOLITE_LOC
from banip.contants import PAD
from banip.contants import TARGETS
from banip.geolite_conversion import make_haproxy
from banip.utilities import clear
from banip.utilities import filter
from banip.utilities import split46


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
        BANNED_IPS,
        CUSTOM_BANS,
        TARGETS,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more info.")
            sys.exit(1)

    # Create the haproxy_geo_ip file.

    make_haproxy()

    # Import target countries

    with open(TARGETS, "r") as f:
        countries = [
            country.upper()
            for line in f
            if (country := line.strip()) and country[0] != "#"
        ]  # fmt: skip

    # Create a dictionary to hold all the generated lists. These are the
    # keys that will be used:

    # CN:  Country subnets.
    # II:  Blacklisted IPs from the ipsum curated list that meet the
    #      minimum confidence factor.
    # BI4: Blacklisted IPv4 addresses from the ipsum curated list that
    #      meet the minimum confidence factor and are also from a target
    #      country.
    # BI6: Blacklisted IPv6 addresses from the ipsum curated list that
    #      meet the minimum confidence factor and are also from a target
    #      country.
    # MI4: My custom blacklisted IPv4 addresses.
    # MI6: My custom blacklisted IPv6 addresses.
    # MN4: My custom blacklisted IPv4 subnets.
    # MN6: My custom blacklisted IPv6 subnets.

    D: dict[str, list[Any]] = {}

    # Placeholders for IP addresses and networks

    bag_of_ips: list[Any]
    bag_of_nets: list[Any]

    # Create a list of all networks for target countries.

    print(f"Pulling networks for country codes: {countries}")
    D["CN"] = filter(COUNTRY_CODES, countries)
    print(f"Networks pulled: {len(D['CN']):,d}")

    # Now process the ipsum file of blacklisted IPs, filtering out those
    # that have less than the desired number of blacklist occurrences
    # (hits)

    print()
    print(f"Pulling blacklisted IPs with >= {args.threshold} hits.")
    D["II"] = filter(BANNED_IPS, args.threshold)
    print(f"IPs pulled: {len(D['II']):,d}")

    # This part takes the longest. Store those blacklisted IPs, with the
    # minimum number of hits that are also hosted on the networks of
    # target countries.

    print()
    bag_of_ips = []
    print(f"Building banned IP list for country codes: {countries}")
    for ip in tqdm(
        D["II"],
        desc="IPs",
        total=len(D["II"]),
        colour="#bf80f2",
        unit="IPs",
    ):
        for network in D["CN"]:
            if ip in network:
                bag_of_ips.append(ip)
                break

    # Separate and sort the banned IPs

    D["BI4"], D["BI6"] = split46(bag_of_ips)
    b_keys = ["BI4", "BI6"]
    for key in b_keys:
        D[key].sort()

    print(f"IPs pulled: {len(bag_of_ips):,d}")

    # Open the custom bans list and prune any IPs or networks that were
    # already discovered while building the list of banned IPs. Finally,
    # create individual lists of IPs/Nets and sort them.

    bag_of_nets = []
    bag_of_ips = []

    with open(CUSTOM_BANS, "r") as f:
        for line in f:
            if token := line.strip():
                if "/" in token:
                    bag_of_nets.append(ipa.ip_network(token))
                else:
                    bag_of_ips.append(ipa.ip_address(token))

    custom_bans = len(bag_of_ips) + len(bag_of_nets)
    duplicates = custom_bans
    bag_of_ips = [ip for
                  ip in bag_of_ips
                  if ip not in D["BI4"] and ip not in D["BI6"]]  # fmt:skip
    duplicates -= len(bag_of_ips) + len(bag_of_nets)
    D["MI4"], D["MI6"] = split46(bag_of_ips)
    D["MN4"], D["MN6"] = split46(bag_of_nets)
    m_keys = ["MI4", "MI6", "MN4", "MN6"]
    for key in m_keys:
        D[key].sort()

    # Overwrite my custom bans list with the duplicates removed. This
    # will also reorder the file as: IPv4, IPv6, Subnets(v4),
    # Subnets(v6)

    with open(CUSTOM_BANS, "w") as f:
        for key in m_keys:
            for chunk in D[key]:
                f.write(f"{format(chunk)}\n")

    # Write banned IPs and custom entries to the file selected on the
    # command line.

    for key in b_keys:
        for ip in D[key]:
            args.outfile.write(f"{format(ip)}\n")

    now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    args.outfile.write("\n# ------------custom entries -------------\n")
    args.outfile.write(f"# Added on: {now}\n")
    args.outfile.write("# ----------------------------------------\n\n")

    for key in m_keys:
        for chunk in D[key]:
            args.outfile.write(f"{format(chunk)}\n")

    # Calculate final metrics and display results.

    ips_found = sum(len(D[key]) for key in b_keys)
    total_bans = ips_found + custom_bans - duplicates

    print(f"\n      Banned IPs found: {ips_found:>{PAD},d}")
    print(f"  Custom bans provided: {custom_bans:>{PAD},d}")
    print(f"    Duplicates removed: {duplicates:>{PAD},d}")
    print(f"Total banned IPs saved: {total_bans:>{PAD},d}")

    return
