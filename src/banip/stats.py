"""Taskrunner for stats command."""

import argparse
import pickle
import textwrap

from rich import box
from rich.console import Console
from rich.style import Style
from rich.table import Table

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import PAD
from banip.constants import NetworkType


def task_runner(args: argparse.Namespace) -> None:
    """Display statistics for a given country.

    Parameters
    ----------
    args : argparse.Namespace
        args.country_code will be the two-letter country code of
        interest.
    """
    if not COUNTRY_NETS_DICT.exists():
        msg = """
        Some required files are missing. Make sure to run the \'build\'
        command before producing statistics for a particular country.
        Run \'banip build -h\' for more information.
        """
        print(textwrap.fill(text=" ".join(msg.split())))
        return

    target_country = args.country_code.upper()
    console = Console()

    print()
    msg = "Loading data"
    with console.status(msg):
        D: dict[NetworkType, str] = {}
        with open(COUNTRY_NETS_DICT, "rb") as f:
            D = pickle.load(f)
    print(f"{msg:.<{PAD}}done")

    msg = "Analyzing"
    results = {"nets_4": 0, "ips_4": 0, "nets_6": 0, "ips_6": 0}
    with console.status(msg):
        for net, country in D.items():
            if country == target_country:
                results[f"nets_{net.version}"] += 1
                results[f"ips_{net.version}"] += (
                    1 if net.num_addresses == 1 else net.num_addresses - 2
                )
    print(f"{msg:.<{PAD}}done")
    print()

    if results == [0] * 4:
        print(f"{target_country} not found")
        return

    no_italic = Style(italic=False)
    table = Table(
        title=f"Results for: {target_country}",
        box=box.SQUARE,
        title_style=no_italic,
        show_header=False,
    )

    table.add_column(justify="right")
    table.add_column(justify="right")

    table.add_row("Nets (v4)", f"{results['nets_4']:,d}")
    table.add_row("Nets (v6)", f"{results['nets_6']:,d}", end_section=True)
    table.add_row("IPs (v4)", f"{results['ips_4']:,d}")
    table.add_row("IPs (v6)", f"{results['ips_6']:.2e}")
    console.print(table)

    return
