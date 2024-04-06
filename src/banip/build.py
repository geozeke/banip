#! /usr/bin/env python3

"""Build a custom list of banned ips."""

import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from tqdm import tqdm  # type: ignore

from banip.constants import BANNED_IPS
from banip.constants import COUNTRY_NETS
from banip.constants import CUSTOM_BLACKLIST
from banip.constants import CUSTOM_WHITELIST
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPS
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import TARGETS
from banip.utilities import clear
from banip.utilities import extract_ip
from banip.utilities import filter
from banip.utilities import ip_in_network
from banip.utilities import split46
from banip.utilities import tag_networks


def task_runner(args: Namespace) -> None:
    """Generate a custom list of banned IP addresses.

    Parameters
    ----------
    args : Namespace
        Command line arguments.
    """
    # Start by stubbing-out custom files if they're not already in
    # place. In the case of the output file, check for two things: (1)
    # Was a file specified? If not, then save results to the default
    # (RENDERED_BLACKLIST). (2) If the file was specified, was it the
    # same name as the default? If so, there's no need to make a local
    # copy of it after computations are complete.
    clear()
    make_local_copy = False
    if not CUSTOM_BLACKLIST.exists():
        f = open(CUSTOM_BLACKLIST, "w")
        f.close()
    if not CUSTOM_WHITELIST.exists():
        f = open(CUSTOM_WHITELIST, "w")
        f.close()
    try:
        if Path(args.outfile.name) != RENDERED_BLACKLIST:
            make_local_copy = True
    except AttributeError:
        args.outfile = open(RENDERED_BLACKLIST, "w")

    # Now make sure everything is in place

    files = [
        BANNED_IPS,
        CUSTOM_BLACKLIST,
        CUSTOM_WHITELIST,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
        RENDERED_BLACKLIST,
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

    # Create the haproxy_geo_ip.txt (COUNTRY_NETS) file.

    tag_networks()

    # Import target countries (two-letter designations, e.g. US)

    with open(TARGETS, "r") as f:
        countries = [
            country.upper()
            for line in f
            if (country := line.strip()) and country[0] != "#"
        ]  # fmt: skip

    # Create a dictionary to hold all generated lists. These are the
    # keys that will be used:

    # CN4: Country subnets (IPv4).
    # CN6: Country subnets (IPv6).
    # II:  Blacklisted IPs from the ipsum.txt curated list that meet the
    #      minimum confidence factor.
    # BI4: Blacklisted IPv4 addresses from the ipsum.txt curated list
    #      that meet the minimum confidence factor and are also from a
    #      target country.
    # BI6: Blacklisted IPv6 addresses from the ipsum.txt curated list
    #      that meet the minimum confidence factor and are also from a
    #      target country.
    # CI4: My custom blacklisted IPv4 addresses.
    # CI6: My custom blacklisted IPv6 addresses.
    # CN4: My custom blacklisted IPv4 subnets.
    # CN6: My custom blacklisted IPv6 subnets.

    D: dict[str, list[Any]] = {}

    # Create a list of all networks for target countries and separate
    # them by IP version, then sort them so we can perform binary
    # searches when determining if a given IP exists in a given network.

    print(f"Pulling networks for country codes: {countries}")
    bag_of_nets = filter(COUNTRY_NETS, countries)
    D["CN4"], D["CN6"] = split46(bag_of_nets)
    D["CN4"].sort()
    D["CN6"].sort()
    print(f"Networks pulled: {len(bag_of_nets):,d}")

    # Now process the ipsum.txt file of blacklisted IPs, filtering out
    # those that have less than the desired number of blacklist
    # occurrences (hits)

    print()
    print(f"Pulling blacklisted IPs with >= {args.threshold} hits.")
    D["II"] = filter(BANNED_IPS, args.threshold)
    print(f"IPs pulled: {len(D['II']):,d}")

    # Store those blacklisted IPs, with the minimum number of hits, that
    # are also hosted on the networks of target countries.

    print()
    bag_of_ips = []
    print(f"Pulling blacklisted IP list for country codes: {countries}")
    for ip in tqdm(
        D["II"],
        desc="Blacklist IPs",
        total=len(D["II"]),
        colour="#bf80f2",
        unit="IPs",
    ):
        if type(ip) is IPv4Address:
            target_net = D["CN4"]
        else:
            target_net = D["CN6"]
        found = ip_in_network(ip, target_net, 0, len(target_net) - 1)
        if found:
            bag_of_ips.append(ip)

    # Separate and sort the blacklisted IPs into IPv4 and IPV6. This is
    # required because you cannot sort a mixed list of v4/v6 items.

    D["BI4"], D["BI6"] = split46(bag_of_ips)
    b_keys = ["BI4", "BI6"]
    for key in b_keys:
        D[key].sort()
    print(f"IPs pulled: {len(bag_of_ips):,d}")

    # Open the custom blacklist and prune any IPs or networks that were
    # already discovered while building the list of blacklisted IPs.
    # Finally, create individual lists of IPs/Nets and sort them. There
    # are two levels of validation: (1) Make sure the input line is not
    # blank, and (2) Make sure a given line converts to either a valid
    # IP address or valid IP subnet. Start by pruning the blacklist to
    # ensure there are no duplicates at the start.

    bag_of_nets = []
    bag_of_ips = []
    with open(CUSTOM_BLACKLIST, "r") as f:
        lines = set(f.readlines())
    for line in lines:
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

    # Overwrite the custom blacklist with the duplicates removed. This
    # will also reorder the file as: IPv4, IPv6, Subnets(v4),
    # Subnets(v6)

    with open(CUSTOM_BLACKLIST, "w") as f:
        for key in c_keys:
            for chunk in D[key]:
                f.write(f"{format(chunk)}\n")

    # Remove any custom whitelisted IPs from the blacklist created by
    # banip. There are two levels of validation: (1) Make sure the input
    # line is not blank, and (2) Make sure the line converts to either a
    # valid IP addess or valid IP subnet.

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

    custom_present = False
    for key in c_keys:
        if len(D[key]) > 0:
            custom_present = True
            break

    if custom_present:
        now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        args.outfile.write("\n# ------------custom entries -------------\n")
        args.outfile.write(f"# Added on: {now}\n")
        args.outfile.write("# ----------------------------------------\n\n")
        for key in c_keys:
            for chunk in D[key]:
                args.outfile.write(f"{format(chunk)}\n")

    args.outfile.close()

    # Save a copy of the generated IP blacklist to
    # ./data/ip_blacklist.txt. This will be used when running banip to
    # check an individual IP address.

    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLACKLIST)

    # Calculate final metrics and display results.

    ips_found = sum(len(D[key]) for key in b_keys)
    total_bans = ips_found + num_custom_blacklist - num_duplicates

    print(f"\n      Banned IPs found: {ips_found:>{PAD},d}")
    print(f"  Custom bans provided: {num_custom_blacklist:>{PAD},d}")
    print(f"    Duplicates removed: {num_duplicates:>{PAD},d}")
    print(f"Total banned IPs saved: {total_bans:>{PAD},d}")

    return


if __name__ == "__main__":
    pass
