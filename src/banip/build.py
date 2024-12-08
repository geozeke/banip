#! /usr/bin/env python3

"""Build a custom list of banned IPs."""

import ipaddress as ipa
import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path

from rich import box
from rich.console import Console
from rich.style import Style
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
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
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
    # networks and addresses. Remove any duplicates using sets.
    console = Console()
    msg = "Pruning custom blacklist"
    with console.status(msg):
        with open(CUSTOM_BLACKLIST, "r") as f:
            custom: list[AddressType | NetworkType] = [
                ip for line in f if (ip := extract_ip(line.strip()))
            ]
        custom_nets = sorted(
            list({token for token in custom if isinstance(token, NetworkType)}),
            key=lambda x: int(x.network_address),
        )
        custom_nets_size = len(custom_nets)
        custom_ips = sorted(
            list({token for token in custom if isinstance(token, AddressType)}),
            key=lambda x: int(x),
        )
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
        geolite_L = sorted(
            [net for net in geolite_D if geolite_D[net] in countries],
            key=lambda x: int(x.network_address),
        )
        geolite_size = len(geolite_L)
    print(f"{msg:.<{PAD}}done")

    # Save the cleaned-up country codes for later use in HAProxy
    msg = "Saving country targets"
    with console.status(msg):
        countries.sort()
        with open(COUNTRY_WHITELIST, "w") as f:
            f.write(f"{"\n".join(countries)}\n")
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Prune ipsum.txt to only keep IPs (1) from target countries, (2)
    # IPs that are not already covered by a custom subnet, (3) IPs that
    # meet the minimum threshold for number of hits, and (4) IPs that
    # are not in the custom whitelist.
    msg = "Pruning ipsum.txt"
    with console.status(msg):
        whitelist: list[AddressType] = []
        with open(CUSTOM_WHITELIST, "r") as f:
            for line in f:
                try:
                    ip = ipa.ip_address(line.strip())
                    whitelist.append(ip)
                except ValueError:
                    continue

        ipsum_D = load_ipsum()
        ipsum_L: list[AddressType] = [
            ip
            for ip in ipsum_D
            if (
                ip_in_network(ip=ip, networks=geolite_L, first=0, last=geolite_size - 1)
                and not ip_in_network(
                    ip=ip, networks=custom_nets, first=0, last=custom_nets_size - 1
                )
                and ip not in whitelist
                and ipsum_D[ip] >= args.threshold
            )
        ]
        ipsum_L = sorted(ipsum_L, key=lambda x: int(x))
        ipsum_size = len(ipsum_L)
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Prune the list of custom IPs again so that what's left are not
    # covered by ipsum.txt, and are IPs from countries that are included
    # in the country whitelist. Account for custom IPs that might not
    # have a country association (e.g. an IP on a local network)
    msg = "Removing redundant IPs"
    with console.status(msg):
        temp_L: list[AddressType] = []
        for ip in custom_ips:
            if ip in ipsum_L or (
                (
                    country_net := ip_in_network(
                        ip=ip, networks=geolite_L, first=0, last=geolite_size - 1
                    )
                )
                and geolite_D[country_net] not in countries
            ):
                continue
            temp_L.append(ip)
        custom_ips = temp_L.copy()
        custom_ips_size = len(custom_ips)
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Re-package and save cleaned-up custom IPs and networks
    msg = "Repackaging custom IPs"
    with console.status(msg):
        with open(CUSTOM_BLACKLIST, "w") as f:
            for ip in custom_ips:
                f.write(f"{ip}\n")
            for net in custom_nets:
                f.write(f"{net}\n")
    print(f"{msg:.<{PAD}}done")

    # ------------------------------------------------------------------

    # Render and save the complete ip_blacklist.txt
    msg = "Rendering blacklist"
    with console.status(msg):
        with open(RENDERED_BLACKLIST, "w") as f:
            for ip in ipsum_L:
                f.write(f"{ip}\n")
            now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("\n# ------------custom entries -------------\n")
            f.write(f"# Added on: {now}\n")
            f.write("# ----------------------------------------\n\n")
            for ip in custom_ips:
                f.write(f"{ip}\n")
            for net in custom_nets:
                f.write(f"{net}\n")
    print(f"{msg:.<{PAD}}done")

    args.outfile.close()
    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLACKLIST)

    # Generate table to display metrics
    total_size = ipsum_size + custom_nets_size + custom_ips_size
    table = Table(
        title="Blacklist Stats", box=box.SQUARE, header_style=Style(bold=False)
    )

    table.add_column(header="Metric", justify="right")
    table.add_column(header="Value", justify="right")

    table.add_row("Target Countries", f"{",".join(countries)}")
    table.add_row("Blacklist IPs from ipsum.txt", f"{(ipsum_size):,d}")
    table.add_row("Custom blacklist IPs", f"{(custom_ips_size):,d}")
    table.add_row("Custom blacklist subnets", f"{(custom_nets_size):,d}")
    table.add_row("Total entries saved", f"{(total_size):,d}")

    print()
    console.print(table)

    return


if __name__ == "__main__":
    pass
