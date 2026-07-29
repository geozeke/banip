#! /usr/bin/env python3

"""Build a custom IP blocklist."""

import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from banip.bots import load_managed_bot_networks
from banip.config import CountryConfig
from banip.config import CountryPolicyMode
from banip.config import load_config
from banip.config import update_denylist
from banip.constants import BOTDATA
from banip.constants import CONFIG
from banip.constants import COUNTRY_ALLOWLIST
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import NetworkType
from banip.constants import RENDERED_ALLOWLIST
from banip.constants import RENDERED_BLOCKLIST
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


def resolve_country_policies(
    countries: CountryConfig,
    geolite: dict[NetworkType, str],
) -> dict[str, set[str]]:
    """Resolve named policies into permitted country codes.

    Parameters
    ----------
    countries : CountryConfig
        Validated named country policies.
    geolite : dict[NetworkType, str]
        GeoLite networks mapped to country labels.

    Returns
    -------
    dict[str, set[str]]
        Permitted country codes keyed by policy name.
    """
    available_codes = set(geolite.values())
    resolved: dict[str, set[str]] = {}
    for name, policy in countries.policies.items():
        if policy.mode is CountryPolicyMode.ALLOWLIST:
            resolved[name] = set(policy.codes)
        else:
            resolved[name] = available_codes - policy.codes
    return resolved


def write_country_policy_files(
    countries: CountryConfig,
    resolved: dict[str, set[str]],
) -> None:
    """Write named and compatibility country allowlists.

    Parameters
    ----------
    countries : CountryConfig
        Validated named country policies.
    resolved : dict[str, set[str]]
        Permitted country codes keyed by policy name.
    """
    current_paths = {
        COUNTRY_ALLOWLIST.with_name(f"country_allowlist_{name}.txt")
        for name in resolved
    }
    for stale_path in COUNTRY_ALLOWLIST.parent.glob("country_allowlist_*.txt"):
        if stale_path not in current_paths:
            stale_path.unlink()

    for name, codes in resolved.items():
        policy_path = COUNTRY_ALLOWLIST.with_name(f"country_allowlist_{name}.txt")
        policy_path.write_text(render_lines(sorted(codes)))

    default_codes = resolved[countries.default_policy]
    COUNTRY_ALLOWLIST.write_text(render_lines(sorted(default_codes)))


def task_runner(args: Namespace) -> None:
    """Generate a custom IP blocklist.

    Parameters
    ----------
    args : Namespace
        Command-line arguments.
    """
    # ------------------------------------------------------------------

    # Start by stubbing-out custom files if they're not already in
    # place. In the case of the output file, check for two things: (1)
    # Was a file specified? If not, then save results to the default
    # (RENDERED_BLOCKLIST). (2) If the file was specified, was it the
    # same name as the default? If so, there's no need to make a local
    # copy of it after computations are complete.
    print()
    make_local_copy = False
    try:
        if Path(args.outfile.name) != RENDERED_BLOCKLIST:
            make_local_copy = True
    except AttributeError:
        args.outfile = RENDERED_BLOCKLIST.open("w")

    # ------------------------------------------------------------------

    # Now make sure everything is in place.
    files = [
        CONFIG,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
        IPSUM,
        RENDERED_BLOCKLIST,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://geozeke.github.io/banip/ for more information.")
            sys.exit(1)

    try:
        config = load_config(CONFIG)
    except (FileNotFoundError, ValueError) as exc:
        print(exc)
        sys.exit(1)

    # ------------------------------------------------------------------

    # Load the custom denylist and split it into separate lists of
    # addresses and networks. Remove any duplicates using sets.
    console = Console()
    msg = status_label("custom_prune")
    with console.status(msg):
        custom = config.denylist
        # Make sure the current host's public-facing IP is not in the
        # custom denylist.
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

    # Geotag all global networks, resolve each named country policy into
    # permitted codes, and build one lookup covering countries allowed by
    # any policy.
    geolite = tag_networks()
    msg = status_label("country_filter")
    with console.status(msg):
        resolved_policies = resolve_country_policies(config.countries, geolite)
        threat_countries = set().union(*resolved_policies.values())
        _, threat_geolite = split_hybrid(
            [net for net, country in geolite.items() if country in threat_countries]
        )
        threat_geolite_lookup = build_network_lookup(threat_geolite)
        write_country_policy_files(config.countries, resolved_policies)
    print(format_status("country_filter"))

    # ------------------------------------------------------------------

    # Prune ipsum.txt to keep only IP addresses that (1) are from target
    # countries, (2) are not already covered by a custom subnet, (3)
    # meet the minimum threshold for number of hits, and (4) are not in
    # the custom allowlist.
    msg = status_label("ipsum_prune")
    with console.status(msg):
        allowlist = config.allowlist
        allow_ips, allow_nets = split_hybrid(allowlist)
        allow_nets_lookup = build_network_lookup(allow_nets)
        ipsum_D = load_ipsum()
        ipsum_L = [
            ip
            for ip, hits in ipsum_D.items()
            if (
                ip_in_network(ip=ip, lookup=threat_geolite_lookup)
                and not ip_in_network(ip=ip, lookup=custom_nets_lookup)
                and ip not in allowlist
                and not ip_in_network(ip=ip, lookup=allow_nets_lookup)
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
            allowlist=allowlist,
            min_num=args.compact,
        )
        ipsum_nets_lookup = build_network_lookup(ipsum_nets)
        ipsum_ips_size = len(ipsum_ips)
        ipsum_nets_size = len(ipsum_nets)
        ipsum_size = ipsum_ips_size + ipsum_nets_size
        ipsum_ips_set = set(ipsum_ips)
        compact_factor = 1 - (ipsum_size / len(ipsum_L)) if ipsum_L else 0
    print(
        format_status("ipsum_compact", f"{compact_factor:<.2%}", compact=args.compact)
    )

    # ------------------------------------------------------------------

    # Prune the list of custom IP addresses again so that remaining
    # entries are not covered by ipsum.txt and are within the combined
    # country-policy threat scope.
    msg = status_label("redundant_remove")
    with console.status(msg):
        custom_ips = [
            ip
            for ip in custom_ips
            if ip not in ipsum_ips_set
            and not ip_in_network(ip=ip, lookup=ipsum_nets_lookup)
            and ip_in_network(ip=ip, lookup=threat_geolite_lookup)
        ]
        custom_ips_size = len(custom_ips)
    print(format_status("redundant_remove"))

    # ------------------------------------------------------------------

    # Repackage and save cleaned-up custom IP addresses and networks.
    msg = status_label("repack")
    with console.status(msg):
        update_denylist([*custom_ips, *custom_nets], path=CONFIG)
    print(format_status("repack"))

    # ------------------------------------------------------------------

    # Render and save the complete ip_blocklist.txt and ip_allowlist.txt.
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
        blocklist_text = render_lines([*ipsum_ips, *ipsum_nets])
        if bot_nets:
            blocklist_text += (
                "\n# ---------managed bot ranges -----------\n"
                + f"# Added on: {now}\n"
                + "# ----------------------------------------\n\n"
            )
            for provider in sorted(managed_bot_networks):
                blocklist_text += f"# {provider}\n"
                blocklist_text += render_lines(managed_bot_networks[provider])
        blocklist_text += (
            "\n# ------------custom entries -------------\n"
            + f"# Added on: {now}\n"
            + "# ----------------------------------------\n\n"
            + render_lines([*custom_ips, *custom_nets])
        )
        RENDERED_BLOCKLIST.write_text(blocklist_text)
        RENDERED_ALLOWLIST.write_text(render_lines([*allow_ips, *allow_nets]))
    print(format_status("lists_render"))

    args.outfile.close()
    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLOCKLIST)

    # Generate tables to display country policy and build metrics. Do
    # not include network and broadcast addresses when calculating total
    # IP addresses.
    total_entries = ipsum_size + bot_nets_size + custom_nets_size + custom_ips_size
    total_ipv4s = 0
    total_ipv6s = 0
    for ips in [ipsum_ips, custom_ips]:
        total_ipv4s += sum([1 for ip in ips if ip.version == 4])
        total_ipv6s += sum([1 for ip in ips if ip.version == 6])
    for nets in [ipsum_nets, bot_nets, custom_nets]:
        total_ipv4s += sum([net.num_addresses - 2 for net in nets if net.version == 4])
        total_ipv6s += sum([net.num_addresses - 2 for net in nets if net.version == 6])

    policy_table = Table(
        title="Country Policies",
        title_style="bold cyan",
        box=box.ROUNDED,
        border_style="bright_black",
        header_style="bold",
        padding=(0, 1),
    )
    policy_table.add_column("Policy", style="bold")
    policy_table.add_column("Mode")
    policy_table.add_column("Configured", justify="right", style="cyan")
    policy_table.add_column("Permitted", justify="right", style="cyan")

    for name, policy in sorted(config.countries.policies.items()):
        policy_name = Text(name)
        if name == config.countries.default_policy:
            policy_name.stylize("green")
            policy_name.append(" (default)", style="dim green")
        mode_style = "green" if policy.mode is CountryPolicyMode.ALLOWLIST else "red"
        policy_table.add_row(
            policy_name,
            Text(policy.mode.value, style=mode_style),
            f"{len(policy.codes):,d}",
            f"{len(resolved_policies[name]):,d}",
        )
    policy_table.add_section()
    policy_table.add_row(
        Text("Threat scope", style="bold"),
        Text("union", style="dim"),
        "",
        f"{len(threat_countries):,d}",
    )

    summary_table = Table(
        title="Final Build Summary",
        title_style="bold cyan",
        box=box.ROUNDED,
        border_style="bright_black",
        header_style="bold",
        padding=(0, 1),
    )
    summary_table.add_column("Source")
    summary_table.add_column("Addresses", justify="right", style="cyan")
    summary_table.add_column("Subnets", justify="right", style="cyan")
    summary_table.add_column("Entries", justify="right", style="cyan")
    summary_table.add_row(
        "Threat feeds",
        f"{ipsum_ips_size:,d}",
        f"{ipsum_nets_size:,d}",
        f"{ipsum_size:,d}",
    )
    summary_table.add_row(
        "Managed bots",
        Text("—", style="dim"),
        f"{bot_nets_size:,d}",
        f"{bot_nets_size:,d}",
    )
    summary_table.add_row(
        "Custom entries",
        f"{custom_ips_size:,d}",
        f"{custom_nets_size:,d}",
        f"{custom_ips_size + custom_nets_size:,d}",
    )
    summary_table.add_section()
    summary_table.add_row(
        Text("Total written", style="bold green"),
        "",
        "",
        Text(f"{total_entries:,d}", style="bold green"),
    )
    summary_table.add_section()
    summary_table.add_row(
        Text("IPv4 coverage", style="dim"),
        "",
        "",
        Text(f"{total_ipv4s:,d}", style="dim cyan"),
    )
    summary_table.add_row(
        Text("IPv6 coverage", style="dim"),
        "",
        "",
        Text(f"{total_ipv6s:.2e}", style="dim cyan"),
    )

    print()
    console.print(policy_table)
    print()
    console.print(summary_table)

    return


if __name__ == "__main__":
    pass
