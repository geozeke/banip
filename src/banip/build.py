#! /usr/bin/env python3

"""Build a custom list of banned IPs."""

import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table

from banip.constants import COUNTRY_WHITELIST
from banip.constants import CUSTOM_BLACKLIST
from banip.constants import CUSTOM_WHITELIST
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import RENDERED_WHITELIST
from banip.constants import TARGETS
from banip.utilities import compact
from banip.utilities import extract_ip
from banip.utilities import get_public_ip
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
from banip.utilities import split_hybrid
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

    # Load the custom blacklist and split it into separate lists of
    # addresses and networks. Remove any duplicates using sets.
    console = Console()
    msg = "Pruning custom blacklist"
    with console.status(msg):
        with open(CUSTOM_BLACKLIST, "r") as f:
            custom = {item for line in f if (item := extract_ip(line.strip()))}
        # Make sure the current host's public-facing IP is not in the
        # custom blacklist.
        if (public_ip := get_public_ip()) and (public_ip in custom):
            custom.remove(public_ip)
        custom_ips, custom_nets = split_hybrid(list(custom))
        custom_nets_size = len(custom_nets)
        # Remove any custom IPs that are covered by existing custom
        # subnets
        custom_ips = [
            ip
            for ip in custom_ips
            if not ip_in_network(
                ip=ip, networks=custom_nets, first=0, last=custom_nets_size - 1
            )
        ]
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Geotag all global networks and save entries for target countries
    geolite_D = tag_networks()
    msg = "Filtering networks"
    with console.status(msg):
        with open(TARGETS, "r") as f:
            countries = [
                token.upper()
                for line in f
                if (token := line.strip()) and token[0] != "#"
            ]
        _, target_geolite = split_hybrid(
            [net for net in geolite_D if geolite_D[net] in countries]
        )
        target_geolite_size = len(target_geolite)

    # Save the cleaned-up country codes for later use in HAProxy
    with console.status(msg):
        countries.sort()
        with open(COUNTRY_WHITELIST, "w") as f:
            country_codes = "\n".join(countries)
            f.write(country_codes + "\n")
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Prune ipsum.txt to only keep IPs (1) from target countries, (2)
    # IPs that are not already covered by a custom subnet, (3) IPs that
    # meet the minimum threshold for number of hits, and (4) IPs that
    # are not in the custom whitelist.
    msg = "Pruning ipsum.txt"
    with console.status(msg):
        with open(CUSTOM_WHITELIST, "r") as f:
            whitelist = [item for line in f if (item := extract_ip(line.strip()))]
        white_ips, white_nets = split_hybrid(whitelist)
        white_nets_size = len(white_nets)
        ipsum_D = load_ipsum()
        ipsum_L = [
            ip
            for ip in ipsum_D
            if (
                ip_in_network(
                    ip=ip,
                    networks=target_geolite,
                    first=0,
                    last=target_geolite_size - 1,
                )
                and not ip_in_network(
                    ip=ip, networks=custom_nets, first=0, last=custom_nets_size - 1
                )
                and ip not in whitelist
                and not ip_in_network(
                    ip=ip, networks=white_nets, first=0, last=white_nets_size - 1
                )
                and ipsum_D[ip] >= args.threshold
            )
        ]
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Compact ipsum. A compact factor of 0 indicates no compaction.
    msg = f"Compacting ipsum ({args.compact})"
    with console.status(msg):
        ipsum_ips, ipsum_nets = compact(
            ip_list=ipsum_L,
            whitelist=whitelist,
            min_num=args.compact,
        )
        ipsum_ips_size = len(ipsum_ips)
        ipsum_nets_size = len(ipsum_nets)
        ipsum_size = ipsum_ips_size + ipsum_nets_size
        compact_factor = 1 - (ipsum_size / len(ipsum_L))
    print(f"{msg:.<{PAD}}{compact_factor:<.2%}")

    # ------------------------------------------------------------------

    # Prune the list of custom IPs again so that what's left are not
    # covered by ipsum.txt, and are IPs from countries that are included
    # in the country whitelist. Do not remove custom IPs that might not
    # have a country association (e.g. an IP on a local network)
    msg = "Removing redundant IPs"
    with console.status(msg):
        custom_ips = [
            ip
            for ip in custom_ips
            if ip not in ipsum_ips
            and not ip_in_network(
                ip=ip, networks=ipsum_nets, first=0, last=ipsum_nets_size - 1
            )
            and ip_in_network(
                ip=ip, networks=target_geolite, first=0, last=target_geolite_size - 1
            )
        ]
        custom_ips_size = len(custom_ips)
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Re-package and save cleaned-up custom IPs and networks
    msg = "Repackaging custom IPs"
    with console.status(msg):
        with open(CUSTOM_BLACKLIST, "w") as f:
            for ip in custom_ips:
                f.write(str(ip) + "\n")
            for net in custom_nets:
                f.write(str(net) + "\n")
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Render and save the complete ip_blacklist.txt and ip_whitelist.txt
    msg = "Rendering lists"
    with console.status(msg):
        with open(RENDERED_BLACKLIST, "w") as f:
            for ip in ipsum_ips:
                f.write(str(ip) + "\n")
            for net in ipsum_nets:
                f.write(str(net) + "\n")
            now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("\n# ------------custom entries -------------\n")
            f.write(f"# Added on: {now}" + "\n")
            f.write("# ----------------------------------------\n\n")
            for ip in custom_ips:
                f.write(str(ip) + "\n")
            for net in custom_nets:
                f.write(str(net) + "\n")
        with open(RENDERED_WHITELIST, "w") as f:
            for ip in white_ips:
                f.write(str(ip) + "\n")
            for net in white_nets:
                f.write(str(net) + "\n")
    print(f"{msg:.<{PAD}}done")

    args.outfile.close()
    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLACKLIST)

    # Generate a table to display metrics. Do not include the network
    # and broadcast addresses when calculating total_ips.
    total_entries = ipsum_size + custom_nets_size + custom_ips_size
    table = Table(title="Final Build Stats", box=box.SQUARE, show_header=False)
    total_ipv4s = 0
    total_ipv6s = 0
    for ips in [ipsum_ips, custom_ips]:
        total_ipv4s += sum([1 for ip in ips if ip.version == 4])
        total_ipv6s += sum([1 for ip in ips if ip.version == 6])
    for nets in [ipsum_nets, custom_nets]:
        total_ipv4s += sum([net.num_addresses - 2 for net in nets if net.version == 4])
        total_ipv6s += sum([net.num_addresses - 2 for net in nets if net.version == 6])
    div_length = max(
        ipsum_ips_size,
        ipsum_nets_size,
        custom_ips_size,
        custom_nets_size,
    )
    div_pad = len(f"{div_length:,d}")

    table.add_column(justify="right")
    table.add_column(justify="right")

    table.add_row("Target Countries", f"{','.join(countries)}", end_section=True)
    table.add_row("IPs - ipsum.txt", f"{(ipsum_ips_size):,d}")
    table.add_row("Subnets - ipsum.txt", f"{(ipsum_nets_size):,d}")
    table.add_row("IPs - custom", f"{(custom_ips_size):,d}")
    table.add_row("Subnets - custom", f"{(custom_nets_size):,d}")
    table.add_row("-" * 19, "-" * div_pad)
    table.add_row("Total entries saved", f"{(total_entries):,d}", end_section=True)
    table.add_row("Individual IPv4s blocked", f"{(total_ipv4s):,d}")
    table.add_row("Individual IPv6s blocked", f"{(total_ipv6s):.2e}")

    print()
    console.print(table)

    return


if __name__ == "__main__":
    pass
