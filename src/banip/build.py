#! /usr/bin/env python3

"""Build a custom list of banned IP addresses."""

import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table

from banip.bots import load_managed_bot_networks
from banip.config import load_config
from banip.config import update_blacklist
from banip.constants import BOTDATA
from banip.constants import CONFIG
from banip.constants import COUNTRY_WHITELIST
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import NetworkType
from banip.constants import RENDERED_BLACKLIST
from banip.constants import RENDERED_WHITELIST
from banip.utilities import build_network_lookup
from banip.utilities import compact
from banip.utilities import format_status
from banip.utilities import get_public_ip
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
from banip.utilities import render_lines
from banip.utilities import split_hybrid
from banip.utilities import status_label
from banip.utilities import tag_networks


def task_runner(args: Namespace) -> None:
    """Generate a custom list of banned IP addresses.

    Parameters
    ----------
    args : Namespace
        Command-line arguments.
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
    try:
        if Path(args.outfile.name) != RENDERED_BLACKLIST:
            make_local_copy = True
    except AttributeError:
        args.outfile = RENDERED_BLACKLIST.open("w")

    # ------------------------------------------------------------------

    # Now make sure everything is in place.
    files = [
        CONFIG,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
        IPSUM,
        RENDERED_BLACKLIST,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more information.")
            sys.exit(1)

    try:
        config = load_config(CONFIG)
    except (FileNotFoundError, ValueError) as exc:
        print(exc)
        sys.exit(1)

    # ------------------------------------------------------------------

    # Load the custom blacklist and split it into separate lists of
    # addresses and networks. Remove any duplicates using sets.
    console = Console()
    msg = status_label("custom_prune")
    with console.status(msg):
        custom = config.blacklist
        # Make sure the current host's public-facing IP is not in the
        # custom blacklist.
        if (public_ip := get_public_ip()) and (public_ip in custom):
            custom.remove(public_ip)
        custom_ips, custom_nets = split_hybrid(custom)
        custom_nets_size = len(custom_nets)
        custom_nets_lookup = build_network_lookup(custom_nets)
        # Remove any custom IP addresses that are covered by existing
        # custom subnets.
        custom_ips = [
            ip
            for ip in custom_ips
            if not ip_in_network(ip=ip, lookup=custom_nets_lookup)
        ]
    print(format_status("custom_prune"))

    # ------------------------------------------------------------------

    # Geotag all global networks and save entries for target countries.
    geolite_D = tag_networks()
    msg = status_label("country_filter")
    with console.status(msg):
        countries = config.targets
        _, target_geolite = split_hybrid(
            [net for net in geolite_D if geolite_D[net] in countries]
        )
        target_geolite_lookup = build_network_lookup(target_geolite)

    # Save the cleaned-up country codes for later use in HAProxy.
    with console.status(msg):
        sorted_countries = sorted(countries)
        COUNTRY_WHITELIST.write_text(render_lines(sorted_countries))
    print(format_status("country_filter"))

    # ------------------------------------------------------------------

    # Prune ipsum.txt to keep only IP addresses that (1) are from target
    # countries, (2) are not already covered by a custom subnet, (3)
    # meet the minimum threshold for number of hits, and (4) are not in
    # the custom whitelist.
    msg = status_label("ipsum_prune")
    with console.status(msg):
        whitelist = config.whitelist
        white_ips, white_nets = split_hybrid(whitelist)
        white_nets_lookup = build_network_lookup(white_nets)
        ipsum_D = load_ipsum()
        ipsum_L = [
            ip
            for ip, hits in ipsum_D.items()
            if (
                ip_in_network(ip=ip, lookup=target_geolite_lookup)
                and not ip_in_network(ip=ip, lookup=custom_nets_lookup)
                and ip not in whitelist
                and not ip_in_network(ip=ip, lookup=white_nets_lookup)
                and hits >= args.threshold
            )
        ]
    print(format_status("ipsum_prune"))

    # ------------------------------------------------------------------

    # Compact ipsum. A compact factor of 0 indicates no compaction.
    msg = status_label("ipsum_compact", compact=args.compact)
    with console.status(msg):
        ipsum_ips, ipsum_nets = compact(
            ip_list=ipsum_L,
            whitelist=whitelist,
            min_num=args.compact,
        )
        ipsum_nets_lookup = build_network_lookup(ipsum_nets)
        ipsum_ips_size = len(ipsum_ips)
        ipsum_nets_size = len(ipsum_nets)
        ipsum_size = ipsum_ips_size + ipsum_nets_size
        ipsum_ips_set = set(ipsum_ips)
        compact_factor = 1 - (ipsum_size / len(ipsum_L))
    print(
        format_status("ipsum_compact", f"{compact_factor:<.2%}", compact=args.compact)
    )

    # ------------------------------------------------------------------

    # Prune the list of custom IP addresses again so that remaining
    # entries are not covered by ipsum.txt and are from countries in the
    # country whitelist. Do not remove custom IP addresses that might
    # not have a country association, such as local-network addresses.
    msg = status_label("redundant_remove")
    with console.status(msg):
        custom_ips = [
            ip
            for ip in custom_ips
            if ip not in ipsum_ips_set
            and not ip_in_network(ip=ip, lookup=ipsum_nets_lookup)
            and ip_in_network(ip=ip, lookup=target_geolite_lookup)
        ]
        custom_ips_size = len(custom_ips)
    print(format_status("redundant_remove"))

    # ------------------------------------------------------------------

    # Repackage and save cleaned-up custom IP addresses and networks.
    msg = status_label("repack")
    with console.status(msg):
        update_blacklist([*custom_ips, *custom_nets], path=CONFIG)
    print(format_status("repack"))

    # ------------------------------------------------------------------

    # Render and save the complete ip_blacklist.txt and ip_whitelist.txt.
    msg = status_label("lists_render")
    with console.status(msg):
        managed_bot_networks: dict[str, list[NetworkType]] = {}
        if (
            config.bots.enabled
            and not getattr(args, "no_bots", False)
            and BOTDATA.exists()
        ):
            managed_bot_networks = load_managed_bot_networks(config.bots.providers)
        bot_nets = [
            net
            for provider in sorted(managed_bot_networks)
            for net in managed_bot_networks[provider]
        ]
        bot_nets_size = len(bot_nets)
        now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        blacklist_text = render_lines([*ipsum_ips, *ipsum_nets])
        if bot_nets:
            blacklist_text += (
                "\n# ---------managed bot ranges -----------\n"
                + f"# Added on: {now}\n"
                + "# ----------------------------------------\n\n"
            )
            for provider in sorted(managed_bot_networks):
                blacklist_text += f"# {provider}\n"
                blacklist_text += render_lines(managed_bot_networks[provider])
        blacklist_text += (
            "\n# ------------custom entries -------------\n"
            + f"# Added on: {now}\n"
            + "# ----------------------------------------\n\n"
            + render_lines([*custom_ips, *custom_nets])
        )
        RENDERED_BLACKLIST.write_text(blacklist_text)
        RENDERED_WHITELIST.write_text(render_lines([*white_ips, *white_nets]))
    print(format_status("lists_render"))

    args.outfile.close()
    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLACKLIST)

    # Generate a table to display metrics. Do not include the network
    # and broadcast addresses when calculating total IP addresses.
    total_entries = ipsum_size + bot_nets_size + custom_nets_size + custom_ips_size
    table = Table(title="Final Build Stats", box=box.SQUARE, show_header=False)
    total_ipv4s = 0
    total_ipv6s = 0
    for ips in [ipsum_ips, custom_ips]:
        total_ipv4s += sum([1 for ip in ips if ip.version == 4])
        total_ipv6s += sum([1 for ip in ips if ip.version == 6])
    for nets in [ipsum_nets, bot_nets, custom_nets]:
        total_ipv4s += sum([net.num_addresses - 2 for net in nets if net.version == 4])
        total_ipv6s += sum([net.num_addresses - 2 for net in nets if net.version == 6])
    div_length = max(
        ipsum_ips_size,
        ipsum_nets_size,
        bot_nets_size,
        custom_ips_size,
        custom_nets_size,
    )
    div_pad = len(f"{div_length:,d}")

    table.add_column(justify="right")
    table.add_column(justify="right")

    table.add_row("Target Countries", f"{','.join(sorted_countries)}", end_section=True)
    table.add_row("IP addresses - ipsum.txt", f"{(ipsum_ips_size):,d}")
    table.add_row("Subnets - ipsum.txt", f"{(ipsum_nets_size):,d}")
    table.add_row("Subnets - managed bots", f"{(bot_nets_size):,d}")
    table.add_row("IP addresses - custom", f"{(custom_ips_size):,d}")
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
