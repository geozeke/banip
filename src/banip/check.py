"""Task runner for the check command."""

import argparse
import pickle
from typing import cast

from rich.console import Console
from rich.style import Style
from rich.table import Table

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import AddressType
from banip.utilities import clear
from banip.utilities import extract_ip
from banip.utilities import format_status
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
from banip.utilities import load_rendered_blacklist
from banip.utilities import split_hybrid
from banip.utilities import status_label


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    """
    print()

    if not COUNTRY_NETS_DICT.exists():
        msg = """
        Some required files are missing. Run the \'build\' command
        before checking an IP address. Run this
        command for more information:
        
        \'banip build -h\'
        """
        print("\n".join([line.strip() for line in msg.split("\n")]))
        return

    console = Console()
    text_green = Style(color="green")
    text_red = Style(color="red")

    # Load ipsum data into a dictionary.
    msg = status_label("ipsum_load_data")
    with console.status(msg):
        ipsum = load_ipsum()
    print(format_status("ipsum_load_data"))

    # Load the rendered blacklist.
    msg = status_label("blacklist_rendered_load")
    with console.status(msg):
        rendered_ips, rendered_nets = load_rendered_blacklist()
    print(format_status("blacklist_rendered_load"))

    # Load geolocation data.
    msg = status_label("geolite_load")
    with console.status(msg):
        with open(COUNTRY_NETS_DICT, "rb") as f:
            nets_D = pickle.load(f)
        _, nets_L = split_hybrid(nets_D.keys())
    print(format_status("geolite_load"))

    # Respond to requests
    while True:
        clear()

        while True:
            user_input = input("IP address: ")
            if ip := extract_ip(user_input):
                target = cast(AddressType, ip)
                break
            print(f"{user_input} is not a valid IP address.")

        table = Table(title=f"Stats for {target}", show_lines=True, show_header=False)
        table.add_column(justify="right")
        table.add_column(justify="right")
        attribute = "Country Code"

        if located_net := ip_in_network(
            ip=target, networks=nets_L, first=0, last=len(nets_L) - 1
        ):
            status = nets_D[located_net], text_green
        else:
            status = "--", text_red
        table.add_row(attribute, status[0], style=status[1])

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

        while (again := input("Search again (y/n)? ").strip().lower()) not in [
            "y",
            "n",
        ]:
            continue
        if again == "n":
            break

    return
