#! /usr/bin/env python3

"""Augment the IP addresses in ipsum.txt."""

import sys
from argparse import Namespace
from typing import cast

from rich import box
from rich.console import Console
from rich.table import Table

from banip.constants import IPSUM
from banip.constants import AddressType
from banip.utilities import extract_ip
from banip.utilities import format_status
from banip.utilities import load_ipsum
from banip.utilities import render_lines
from banip.utilities import status_label


def task_runner(args: Namespace) -> None:
    """Augment the addresses in ipsum.txt.

    Parameters
    ----------
    args : Namespace
        Command-line arguments.
    """
    # ------------------------------------------------------------------

    console = Console()

    # Make sure everything is in place.
    files = [IPSUM]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more information.")
            sys.exit(1)

    # Load ipsum.txt.
    msg = status_label("ipsum_load")
    with console.status(msg):
        ipsum = load_ipsum()
    print(format_status("ipsum_load"))

    original_ipsum_size = len(ipsum)
    new_ips_considered = 0

    # Start patching.
    msg = status_label("ipsum_patch")
    with console.status(msg):
        for line in args.newips:
            parts = line.split()
            try:
                raw_ip = parts[args.index]
            except IndexError:
                continue
            if ip := cast(AddressType, extract_ip(raw_ip)):
                new_ips_considered += 1
                if (ip not in ipsum) or (ipsum[ip] < args.confidence):
                    ipsum[ip] = args.confidence
    print(format_status("ipsum_patch"))
    new_ips_added = len(ipsum) - original_ipsum_size

    # Update the file on disk.
    IPSUM.write_text(render_lines(f"{ip} {hits}" for ip, hits in ipsum.items()))

    # Generate a table to display metrics.
    table = Table(title="Final Augmentation Stats", box=box.SQUARE, show_header=False)
    table.add_column(justify="right")
    table.add_column(justify="right")

    table.add_row("Original ipsum.txt size", f"{(original_ipsum_size):,d}")
    table.add_row("New IP addresses analyzed", f"{(new_ips_considered):,d}")
    table.add_row("New IP addresses added", f"{(new_ips_added):,d}")
    table.add_row("New ipsum.txt size", f"{(len(ipsum)):,d}")

    print()
    console.print(table)
    args.newips.close()

    return


if __name__ == "__main__":
    pass
