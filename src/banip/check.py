"""Taskrunner for check command."""

import argparse
import ipaddress as ipa
import pickle
import textwrap

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
    text_green = Style(color="green")
    text_red = Style(color="red")

    # Load ipsum file into a dictionary
    msg = "Loading ipsum data"
    with console.status(msg):
        ipsum = load_ipsum()
    print(f"{msg:.<{PAD}}done")

    # Load rendered blacklist and split it into separate lists of
    # networks and ip addresses
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
            rendered_ips = sorted(
                [token for token in rendered if isinstance(token, AddressType)],
                key=lambda x: int(x),
            )
    print(f"{msg:.<{PAD}}done")

    # Start building the table
    table = Table(title=f"Stats for {target}", show_lines=True)
    table.add_column(header="Attribute", justify="right")
    table.add_column(header="Result", justify="right")

    # Load the HAProxy countries dictionary, arrange sorted keys, and
    # locate the two-letter country code for target ip.
    msg = "Finding country of origin"
    attribute = "Country Code"
    with console.status(msg):
        with open(COUNTRY_NETS_DICT, "rb") as f:
            nets_D = pickle.load(f)
        nets_L = sorted(nets_D.keys(), key=lambda x: int(x.network_address))
        if located_net := ip_in_network(
            ip=target, networks=nets_L, first=0, last=len(nets_L) - 1
        ):
            status = nets_D[located_net], text_green
        else:
            status = "--", text_red
    table.add_row(attribute, status[0], style=status[1])
    print(f"{msg:.<{PAD}}done")

    # Check for membership in the rendered blacklist
    attribute = "Rendered Blacklist"
    if ip_in_network(
        ip=target, networks=rendered_nets, first=0, last=len(rendered_nets) - 1
    ):
        status = "found in subnet", text_green
    elif target in rendered_ips:
        status = "found", text_green
    else:
        status = "not found", text_red
    table.add_row(attribute, status[0], style=status[1])

    # Check for membership in ipsum.txt
    attribute = "ipsum.txt"
    if target in ipsum:
        status = f"found ({ipsum[target]})", text_green
    else:
        status = "not found", text_red
    table.add_row(attribute, status[0], style=status[1])

    print()
    console.print(table)

    return
