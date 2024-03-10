#! /usr/bin/env python3

"""Build a custom list of banned ips."""

import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path
from typing import Any

from tqdm import tqdm  # type: ignore

from banip.contants import BANNED_IPS
from banip.contants import COUNTRY_NETS
from banip.contants import CUSTOM_BLACKLIST
from banip.contants import CUSTOM_WHITELIST
from banip.contants import GEOLITE_4
from banip.contants import GEOLITE_6
from banip.contants import GEOLITE_LOC
from banip.contants import IPS
from banip.contants import PAD
from banip.contants import RENDERED_BLACKLIST
from banip.contants import TARGETS
from banip.utilities import clear
from banip.utilities import extract_ip
from banip.utilities import filter
from banip.utilities import split46
from banip.utilities import tag_networks


def banned_ips(args: Namespace) -> None:
    """Generate a custom list of banned IP addresses.

    Parameters
    ----------
    args : Namespace
        Command line arguments.
    """
    clear()

    # Start by stubbing-out custom files if they're not already in
    # place.

    if not CUSTOM_BLACKLIST.exists():
        f = open(CUSTOM_BLACKLIST, "w")
        f.close()
    if not CUSTOM_WHITELIST.exists():
        f = open(CUSTOM_WHITELIST, "w")
        f.close()

    # Now make sure everything is in place

    files = [
        BANNED_IPS,
        CUSTOM_BLACKLIST,
        CUSTOM_WHITELIST,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
        TARGETS,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more info.")
            sys.exit(1)

    # Placeholders for IP addresses and networks

    bag_of_ips: list[Any]
    bag_of_nets: list[Any]

    # Create the haproxy_geo_ip (COUNTRY_NETS) file.

    tag_networks()

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
    # CI4: My custom blacklisted IPv4 addresses.
    # CI6: My custom blacklisted IPv6 addresses.
    # CN4: My custom blacklisted IPv4 subnets.
    # CN6: My custom blacklisted IPv6 subnets.

    D: dict[str, list[Any]] = {}

    # Create a list of all networks just for target countries.

    print(f"Pulling networks for country codes: {countries}")
    D["CN"] = filter(COUNTRY_NETS, countries)
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
    print(f"Building blacklisted IP list for country codes: {countries}")
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

    # Separate and sort the blacklisted IPs into IPv4 and IPV6. This is
    # required, because you cannot sort a mixed list of v4/v6 items.

    D["BI4"], D["BI6"] = split46(bag_of_ips)
    b_keys = ["BI4", "BI6"]
    for key in b_keys:
        D[key].sort()

    print(f"IPs pulled: {len(bag_of_ips):,d}")

    # Open the custom blacklist and prune any IPs or networks that were
    # already discovered while building the list of blacklisted IPs.
    # Finally, create individual lists of IPs/Nets and sort them. There
    # are two levels of validation: (1) Make sure the input line is not
    # blank, and (2) Make sure the line converts to either a valid IP
    # addess or valid IP subnet.

    bag_of_nets = []
    bag_of_ips = []
    with open(CUSTOM_BLACKLIST, "r") as f:
        for line in f:
            if token := line.strip():
                if ip := extract_ip(token):
                    if type(ip) in IPS:
                        bag_of_ips.append(ip)
                    else:
                        bag_of_nets.append(ip)

    num_custom_blacklist = len(bag_of_ips) + len(bag_of_nets)
    num_duplicates = num_custom_blacklist
    bag_of_ips = [ip for
                  ip in bag_of_ips
                  if ip not in D["BI4"] and ip not in D["BI6"]]  # fmt:skip
    num_duplicates -= len(bag_of_ips) + len(bag_of_nets)
    D["CI4"], D["CI6"] = split46(bag_of_ips)
    D["CN4"], D["CN6"] = split46(bag_of_nets)
    c_keys = ["CI4", "CI6", "CN4", "CN6"]
    for key in c_keys:
        D[key].sort()

    # Overwrite my custom blacklist with the duplicates removed. This
    # will also reorder the file as: IPv4, IPv6, Subnets(v4),
    # Subnets(v6)

    with open(CUSTOM_BLACKLIST, "w") as f:
        for key in c_keys:
            for chunk in D[key]:
                f.write(f"{format(chunk)}\n")

    # Remove any custom whitelisted IPs from those that may have been
    # found by banip. There are two levels of validation: (1) Make sure
    # the input line is not blank, and (2) Make sure the line converts
    # to either a valid IP addess or valid IP subnet.

    whitelist: Any = []
    with open(CUSTOM_WHITELIST, "r") as f:
        for line in f:
            if token := line.strip():
                if ip := extract_ip(token):
                    whitelist.append(ip)

    for token in whitelist:
        if token in D["BI4"]:
            D["BI4"].remove(token)
        elif token in D["BI6"]:
            D["BI6"].remove(token)

    # Write blacklisted IPs and custom entries to the file selected on
    # the command line.

    for key in b_keys:
        for ip in D[key]:
            args.outfile.write(f"{format(ip)}\n")

    now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    args.outfile.write("\n# ------------custom entries -------------\n")
    args.outfile.write(f"# Added on: {now}\n")
    args.outfile.write("# ----------------------------------------\n\n")

    for key in c_keys:
        for chunk in D[key]:
            args.outfile.write(f"{format(chunk)}\n")

    # Save a copy of the generated IP blacklist to
    # ./data/ip_blacklist.txt. This will be used when running banip to
    # check an individual IP address.

    if Path(args.outfile.name) != RENDERED_BLACKLIST:
        shutil.copyfile(args.outfile.name, RENDERED_BLACKLIST)

    # Calculate final metrics and display results.

    ips_found = sum(len(D[key]) for key in b_keys)
    total_bans = ips_found + num_custom_blacklist - num_duplicates

    print(f"\n      Banned IPs found: {ips_found:>{PAD},d}")
    print(f"  Custom bans provided: {num_custom_blacklist:>{PAD},d}")
    print(f"    Duplicates removed: {num_duplicates:>{PAD},d}")
    print(f"Total banned IPs saved: {total_bans:>{PAD},d}")

    return
