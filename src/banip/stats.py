"""Task runner for the stats command."""

import argparse
import pickle

from rich import box
from rich.console import Console
from rich.style import Style
from rich.table import Table

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import NetworkType
from banip.utilities import format_status
from banip.utilities import status_label


def task_runner(args: argparse.Namespace) -> None:
    """Display statistics for a given country.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    """
    if not COUNTRY_NETS_DICT.exists():
        msg = """
        Some required files are missing. Run the \'build\'
        command before generating statistics for a given country. Run
        this command for more information:
        
        \'banip build -h\'
        """
        print("\n".join([line.strip() for line in msg.split("\n")]))
        return

    target_country = args.country_code.upper()
    console = Console()

    print()
    msg = status_label("stats_load")
    with console.status(msg):
        D: dict[NetworkType, str] = {}
        with COUNTRY_NETS_DICT.open("rb") as f:
            D = pickle.load(f)
    print(format_status("stats_load"))

    msg = status_label("analyze")
    results = {"nets_4": 0, "ips_4": 0, "nets_6": 0, "ips_6": 0}
    with console.status(msg):
        for net, country in D.items():
            if country == target_country:
                results[f"nets_{net.version}"] += 1
                results[f"ips_{net.version}"] += (
                    1 if net.num_addresses == 1 else net.num_addresses - 2
                )
    print(format_status("analyze"))
    print()

    if all(value == 0 for value in results.values()):
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

    table.add_row("Networks (v4)", f"{results['nets_4']:,d}")
    table.add_row("Networks (v6)", f"{results['nets_6']:,d}", end_section=True)
    table.add_row("IP addresses (v4)", f"{results['ips_4']:,d}")
    table.add_row("IP addresses (v6)", f"{results['ips_6']:.2e}")
    console.print(table)

    return
