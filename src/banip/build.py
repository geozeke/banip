#! /usr/bin/env python3

"""Build a custom list of banned ips."""

import ipaddress as ipa
import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path

from banip.constants import CUSTOM_BLACKLIST
from banip.constants import CUSTOM_WHITELIST
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network
from banip.utilities import tag_networks


def task_runner(args: Namespace) -> None:
    """Generate a custom list of banned IP addresses.

    Parameters
    ----------
    args : Namespace
        Command line arguments.
    """
    # ------------------------------------------------------------------

    # Start by stubbing-out custom files if they're not already in
    # place. In the case of the output file, check for two things: (1)
    # Was a file specified? If not, then save results to the default
    # (RENDERED_BLACKLIST). (2) If the file was specified, was it the
    # same name as the default? If so, there's no need to make a local
    # copy of it after computations are complete.
    print()
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

    # ------------------------------------------------------------------

    # Now make sure everything is in place
    files = [
        CUSTOM_BLACKLIST,
        CUSTOM_WHITELIST,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
        IPSUM,
        RENDERED_BLACKLIST,
        TARGETS,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more info.")
            sys.exit(1)

    # ------------------------------------------------------------------

    # Load custom blacklist and split it into lists of networks and
    # addresses
    print(f"{'Pruning custom blacklist':.<{PAD}}", end="", flush=True)
    with open(CUSTOM_BLACKLIST, "r") as f:
        custom: list[AddressType | NetworkType] = [
            ip for line in f if (ip := extract_ip(line.strip()))
        ]
    custom_nets: list[NetworkType] = sorted(
        [token for token in custom if isinstance(token, NetworkType)],
        key=lambda x: int(x.network_address),
    )
    custom_nets_size = len(custom_nets)
    custom_ips: list[AddressType] = sorted(
        [token for token in custom if isinstance(token, AddressType)],
        key=lambda x: int(x),
    )
    # Remove any custom ips that are covered by existing custom subnets
    custom_ips = [
        ip
        for ip in custom_ips
        if not ip_in_network(
            ip=ip, networks=custom_nets, first=0, last=custom_nets_size - 1
        )
    ]
    print("done")

    # ------------------------------------------------------------------

    # Geo-tag all global networks and save entries for target countries
    geolite_D = tag_networks()
    with open(TARGETS, "r") as f:
        countries = [
            token.upper() for line in f if (token := line.strip()) and token[0] != "#"
        ]
    geolite = sorted(
        [key for key in geolite_D if geolite_D[key] in countries],
        key=lambda x: int(x.network_address),
    )
    geolite_size = len(geolite)

    # ------------------------------------------------------------------

    # Prune ipsum.txt to only keep ips from target countries, ips that
    # are not already covered by a custom subnet, ips that meet the
    # minimum threshold for number of hits, and ips that are not in the
    # custom whitelist.
    print(f"{'Pruning ipsum.txt':.<{PAD}}", end="", flush=True)
    whitelist: list[AddressType] = []
    with open(CUSTOM_WHITELIST, "r") as f:
        for line in f:
            try:
                ip = ipa.ip_address(line.strip())
            except ValueError:
                continue
    with open(IPSUM, "r") as f:
        ipsum: list[AddressType] = []
        for line in f:
            parts = line.strip().split()
            try:
                ip = ipa.ip_address(parts[0])
                hits = int(parts[1])
            except (ValueError, NameError):
                continue
            if (
                ip_in_network(ip=ip, networks=geolite, first=0, last=geolite_size - 1)
                and not ip_in_network(
                    ip=ip,
                    networks=custom_nets,
                    first=0,
                    last=custom_nets_size - 1,
                )
                and ip not in whitelist
                and (hits >= args.threshold)
            ):
                ipsum.append(ip)
        ipsum = sorted(ipsum, key=lambda x: int(x))
        ipsum_size = len(ipsum)
        print("done")

    # ------------------------------------------------------------------

    # Prune any custom ips that are covered by ipsum.txt.
    print(f"{'De-duplicating custom ips':.<{PAD}}", end="", flush=True)
    custom_ips = [ip for ip in custom_ips if ip not in ipsum]
    custom_ips_size = len(custom_ips)
    print("done")

    # ------------------------------------------------------------------

    # Re-package and save cleaned-up custom nets and ips
    print(f"{'Re-packaging custom ips':.<{PAD}}", end="", flush=True)
    with open(CUSTOM_BLACKLIST, "w") as f:
        for ip in custom_ips:
            f.write(f"{ip}\n")
        for net in custom_nets:
            f.write(f"{net}\n")
    print("done")

    # ------------------------------------------------------------------

    # Render and save the complete ip_blacklist.txt
    print(f"{'Rendering blacklist':.<{PAD}}", end="", flush=True)
    with open(RENDERED_BLACKLIST, "w") as f:
        for ip in ipsum:
            f.write(f"{ip}\n")
        now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write("\n# ------------custom entries -------------\n")
        f.write(f"# Added on: {now}\n")
        f.write("# ----------------------------------------\n\n")
        for ip in custom_ips:
            f.write(f"{ip}\n")
        for net in custom_nets:
            f.write(f"{net}\n")
    print("done")

    args.outfile.close()
    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLACKLIST)

    print(f"{'Blacklist entries saved':.<{PAD}}", end="", flush=True)
    total_size = ipsum_size + custom_nets_size + custom_ips_size
    print(f"{(total_size):,d}")

    # # Placeholders for IP addresses and networks

    # list_of_ips: list[Any]
    # list_of_nets: list[Any]

    # # Create the haproxy_geo_ip.txt (COUNTRY_NETS) file.

    # tag_networks()

    # # Import target countries (two-letter designations, e.g. US)

    # with open(TARGETS, "r") as f:
    #     countries = [
    #         country.upper()
    #         for line in f
    #         if (country := line.strip()) and country[0] != "#"
    #     ]  # fmt: skip

    # # Create a dictionary to hold all generated lists. These are the
    # # keys that will be used:

    # # CN4: Country subnets (IPv4).
    # # CN6: Country subnets (IPv6).
    # # II:  Blacklisted IPs from the ipsum.txt curated list that meet the
    # #      minimum confidence factor.
    # # BI4: Blacklisted IPv4 addresses from the ipsum.txt curated list
    # #      that meet the minimum confidence factor and are also from a
    # #      target country.
    # # BI6: Blacklisted IPv6 addresses from the ipsum.txt curated list
    # #      that meet the minimum confidence factor and are also from a
    # #      target country.
    # # CI4: My custom blacklisted IPv4 addresses.
    # # CI6: My custom blacklisted IPv6 addresses.
    # # CN4: My custom blacklisted IPv4 subnets.
    # # CN6: My custom blacklisted IPv6 subnets.

    # keys_blacklist = ["BI4", "BI6"]
    # keys_custom = ["CI4", "CI6", "CN4", "CN6"]
    # keys_ips = ["BI4", "BI6", "CI4", "CI6"]
    # keys_networks = ["CN4", "CN6"]
    # D: dict[str, list[Any]] = {}

    # # Create a list of all networks for target countries and separate
    # # them by IP version, then sort them so we can perform binary
    # # searches when determining if a given IP exists in a given network.

    # print(f"Pulling networks for country codes: {countries}")
    # list_of_nets = filter(COUNTRY_NETS, countries)
    # D["CN4"], D["CN6"] = split46(list_of_nets)
    # D["CN4"].sort()
    # D["CN6"].sort()
    # print(f"Networks pulled: {len(list_of_nets):,d}")

    # # Now process the ipsum.txt file of blacklisted IPs, filtering out
    # # those that have less than the desired number of blacklist
    # # occurrences (hits)

    # print()
    # print(f"Pulling blacklisted IPs with >= {args.threshold} hits.")
    # D["II"] = filter(IPSUM, args.threshold)
    # print(f"IPs pulled: {len(D['II']):,d}")

    # # Store those blacklisted IPs, with the minimum number of hits, that
    # # are also hosted on the networks of target countries.

    # print()
    # list_of_ips = []
    # print(f"Pulling blacklisted IP list for country codes: {countries}")
    # for ip in tqdm(
    #     D["II"],
    #     desc="Blacklist IPs",
    #     total=len(D["II"]),
    #     colour="#bf80f2",
    #     unit="IPs",
    # ):
    #     if type(ip) is IPv4Address:
    #         target_nets = D["CN4"]
    #     else:
    #         target_nets = D["CN6"]
    #     if ip_in_network(ip, target_nets, 0, len(target_nets) - 1):
    #         list_of_ips.append(ip)

    # # Separate and sort the blacklisted IPs into IPv4 and IPV6. This is
    # # required because you cannot sort a mixed list of v4/v6 items.

    # D["BI4"], D["BI6"] = split46(list_of_ips)
    # for key in keys_blacklist:
    #     D[key].sort()
    # ips_found = sum(len(D[key]) for key in keys_blacklist)
    # print(f"IPs pulled: {len(list_of_ips):,d}")

    # # Open the custom blacklist and prune any IPs or networks that were
    # # already discovered while building the list of blacklisted IPs.
    # # Finally, create individual lists of IPs/Nets and sort them. There
    # # are two levels of validation: (1) Make sure the input line is not
    # # blank, and (2) Make sure a given line converts to either a valid
    # # IP address or valid IP subnet. Start by pruning the blacklist to
    # # ensure there are no duplicates at the start.

    # list_of_nets = []
    # list_of_ips = []
    # with open(CUSTOM_BLACKLIST, "r") as f:
    #     lines = set(f.readlines())
    # for line in lines:
    #     if token := line.strip():
    #         if ip := extract_ip(token):
    #             if type(ip) in IPS:
    #                 list_of_ips.append(ip)
    #             else:
    #                 list_of_nets.append(ip)

    # num_custom_blacklist = len(list_of_ips) + len(list_of_nets)
    # num_duplicates = num_custom_blacklist
    # list_of_ips = [ip for
    #                ip in list_of_ips
    #                if ip not in D["BI4"] and ip not in D["BI6"]]  # fmt:skip
    # num_duplicates -= len(list_of_ips) + len(list_of_nets)
    # D["CI4"], D["CI6"] = split46(list_of_ips)
    # D["CN4"], D["CN6"] = split46(list_of_nets)
    # for key in keys_custom:
    #     D[key].sort()

    # # Remove any custom whitelisted IPs from the blacklist created by
    # # banip. There are two levels of validation: (1) Make sure the input
    # # line is not blank, and (2) Make sure the line converts to either a
    # # valid IP addess or valid IP subnet.

    # whitelist: list[Any] = []
    # with open(CUSTOM_WHITELIST, "r") as f:
    #     for line in f:
    #         if token := line.strip():
    #             if ip := extract_ip(token):
    #                 whitelist.append(ip)

    # for token in whitelist:
    #     if token in D["BI4"]:
    #         D["BI4"].remove(token)
    #     elif token in D["BI6"]:
    #         D["BI6"].remove(token)

    # # Remove any individual IP addresses that are already covered by a
    # # custom IP subnet. Do this for both the rendered blacklist, as well
    # # as the custom blacklist.

    # for network in keys_networks:
    #     for ipaddress in keys_ips:
    #         if ipaddress[-1] != network[-1]:
    #             continue
    #         dupe_ips = [
    #             ip
    #             for ip in D[ipaddress]
    #             if any(ip in subnet for subnet in D[network])
    #         ]  # fmt: skip
    #         for ip in dupe_ips:
    #             D[ipaddress].remove(ip)
    #             num_duplicates += 1

    # # Overwrite the provided custom blacklist with the duplicates
    # # removed. This will also reorder the file as: IPv4, IPv6,
    # # Subnets(v4), Subnets(v6)

    # with open(CUSTOM_BLACKLIST, "w") as f:
    #     for key in keys_custom:
    #         for chunk in D[key]:
    #             f.write(f"{format(chunk)}\n")

    # # Write blacklisted IPs and custom entries to the file selected on
    # # the command line.

    # for key in keys_blacklist:
    #     for ip in D[key]:
    #         args.outfile.write(f"{format(ip)}\n")

    # custom_present = False
    # for key in keys_custom:
    #     if len(D[key]) > 0:
    #         custom_present = True
    #         break

    # if custom_present:
    #     now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    #     args.outfile.write("\n# ------------custom entries -------------\n")
    #     args.outfile.write(f"# Added on: {now}\n")
    #     args.outfile.write("# ----------------------------------------\n\n")
    #     for key in keys_custom:
    #         for token in D[key]:
    #             args.outfile.write(f"{format(token)}\n")

    # args.outfile.close()

    # # Save a copy of the generated IP blacklist to
    # # ./data/ip_blacklist.txt. This will be used when running banip to
    # # check an individual IP address.

    # # Calculate final metrics and display results.

    # total_bans = ips_found + num_custom_blacklist - num_duplicates

    # print(f"\n    Banned IPs found: {ips_found:>{PAD},d}")
    # print(f"Custom bans provided: {num_custom_blacklist:>{PAD},d}")
    # print(f"  Duplicates removed: {num_duplicates:>{PAD},d}")
    # print(f"    Total bans saved: {total_bans:>{PAD},d}")

    return


if __name__ == "__main__":
    pass
