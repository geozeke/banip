"""Taskrunner for check command."""

import argparse
import ipaddress as ipa
import pickle

from rich.console import Console
from rich.style import Style
from rich.table import Table

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import PAD
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
from banip.utilities import load_rendered_blacklist
from banip.utilities import split_hybrid


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
        Some required files are missing. Make sure to run the \'build\'
        command before generating statistics for a given IP. Run this
        command for more information:
        
        \'banip build -h\'
        """
        print("\n".join([line.strip() for line in msg.split("\n")]))
        return

    console = Console()
    text_green = Style(color="green")
    text_red = Style(color="red")

    # Load ipsum file into a dictionary
    msg = "Loading ipsum data"
    with console.status(msg):
        ipsum = load_ipsum()
    print(f"{msg:.<{PAD}}done")

    # Load rendered blacklist
    msg = "Loading rendered blacklist"
    with console.status(msg):
        rendered_ips, rendered_nets = load_rendered_blacklist()
    print(f"{msg:.<{PAD}}done")

    # Start building the table
    table = Table(title=f"Stats for {target}", show_lines=True, show_header=False)
    table.add_column(justify="right")
    table.add_column(justify="right")

    # Load the HAProxy countries dictionary, arrange sorted keys, and
    # locate the two-letter country code for target IP.
    msg = "Finding country of origin"
    attribute = "Country Code"
    with console.status(msg):
        with open(COUNTRY_NETS_DICT, "rb") as f:
            nets_D = pickle.load(f)
        _, nets_L = split_hybrid(nets_D.keys())
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
        status = "found in subnet", text_red
    elif target in rendered_ips:
        status = "found", text_red
    else:
        status = "not found", text_green
    table.add_row(attribute, status[0], style=status[1])

    # Check for membership in ipsum.txt
    attribute = "ipsum.txt"
    if target in ipsum:
        status = f"found ({ipsum[target]})", text_red
    else:
        status = "not found", text_green
    table.add_row(attribute, status[0], style=status[1])

    print()
    console.print(table)

    return
