"""Taskrunner for check command."""

import argparse
import ipaddress as ipa
import pickle
import textwrap

from rich import box
from rich.console import Console
from rich.style import Style
from rich.table import Table

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    args : argparse.Namespace
        args.ip will be either IPv4 or IPv6 address of interest.
    """
    print()
    try:
        target = ipa.ip_address(args.ip)
    except ValueError:
        print(f"{args.ip} is not a valid IP address.")
        return

    if not COUNTRY_NETS_DICT.exists():
        msg = """
        Some required files are missing. Make sure to build the
        databases before checking for a particular ip address. Run
        \'banip build -h\' for more information.
        """
        print(textwrap.fill(text=" ".join(msg.split())))
        return

    console = Console()

    # Load ipsum file into a dictionary
    msg = "Loading ipsum data"
    with console.status(msg):
        ipsum = load_ipsum()
    print(f"{msg:.<{PAD}}done")

    # Load rendered blacklist and split into networks and ip addresses
    msg = "Loading rendered blacklist"
    with console.status(msg):
        with open(RENDERED_BLACKLIST, "r") as f:
            rendered: list[AddressType | NetworkType] = [
                token for line in f if (token := extract_ip(line.strip()))
            ]
            rendered_nets = sorted(
                [token for token in rendered if isinstance(token, NetworkType)],
                key=lambda x: int(x.network_address),
            )
            rendered_nets_size = len(rendered_nets)
            rendered_ips = sorted(
                [token for token in rendered if isinstance(token, AddressType)],
                key=lambda x: int(x),
            )
    print(f"{msg:.<{PAD}}done")

    # Load the HAProxy countries dictionary, arrange sorted keys, and
    # locate two-letter country code for target ip.
    msg = "Finding country of origin"
    with console.status(msg):
        with open(COUNTRY_NETS_DICT, "rb") as f:
            nets_D = pickle.load(f)
        nets_L = sorted(nets_D.keys(), key=lambda x: int(x.network_address))
        if located_net := ip_in_network(
            ip=target, networks=nets_L, first=0, last=len(nets_L) - 1
        ):
            country_code = nets_D[located_net]
        else:
            country_code = "--"
    print(f"{msg:.<{PAD}}done")

    # Start building the table
    table = Table(
        title=f"Stats for {target}",
        box=box.HEAVY_HEAD,
        header_style=Style(bold=False),
        show_lines=True,
    )
    table.add_column(header="Metric", justify="right")
    table.add_column(header="Value", justify="right")

    table.add_row("Country Code", country_code)

    # Check for membership in the rendered blacklist
    in_subnet = ip_in_network(
        ip=target, networks=rendered_nets, first=0, last=rendered_nets_size - 1
    )
    if target in rendered_ips or in_subnet:
        if in_subnet:
            table.add_row(
                "Rendered Blacklist",
                "found in subnet",
                style=Style(color="green"),
            )
        else:
            table.add_row(
                "Rendered Blacklist",
                "found",
                style=Style(color="green"),
            )
    else:
        table.add_row(
            "Rendered Blacklist",
            "not found",
            style=Style(color="red"),
        )

    # Check for membership in ipsum.txt
    if target in ipsum:
        table.add_row(
            "ipsum.txt",
            f"found ({ipsum[target]})",
            style=Style(color="green"),
        )
    else:
        table.add_row(
            "ipsum.txt",
            "not found",
            style=Style(color="red"),
        )

    print()
    console.print(table)

    return
