#! /usr/bin/env python3

"""Augment the IP addresses in ipsum.txt."""

import sys
from argparse import Namespace
from typing import cast

from rich import box
from rich.console import Console
from rich.table import Table

from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import AddressType
from banip.utilities import extract_ip
from banip.utilities import load_ipsum


def task_runner(args: Namespace) -> None:
    """Augment the addresses in ipsum.txt.

    Parameters
    ----------
    args : Namespace
        Command line arguments.
    """
    # ------------------------------------------------------------------

    console = Console()

    # Make sure everything is in place
    files = [IPSUM]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more info.")
            sys.exit(1)

    # Load ipsum.txt
    msg = "Loading ipsum.txt"
    with console.status(msg):
        ipsum = load_ipsum()
    print(f"{msg:.<{PAD}}done")

    original_ipsum_size = len(ipsum)
    new_ips_considered = 0

    # Start patching.
    msg = "Patching with new IPs"
    with console.status(msg):
        for line in args.newips:
            parts = line.split()
            if ip := cast(AddressType, extract_ip(parts[args.index])):
                new_ips_considered += 1
                if (ip not in ipsum) or (ipsum[ip] < args.confidence):
                    ipsum[ip] = args.confidence
    print(f"{msg:.<{PAD}}done")
    new_ips_added = len(ipsum) - original_ipsum_size

    # Update file on disk
    with open(IPSUM, "w") as f:
        for k, v in ipsum.items():
            f.write(f"{k} {v}" + "\n")

    # Generate a table to display metrics.
    table = Table(title="Final Augmentation Stats", box=box.SQUARE, show_header=False)
    table.add_column(justify="right")
    table.add_column(justify="right")

    table.add_row("Original ipsum.txt size", f"{(original_ipsum_size):,d}")
    table.add_row("New IPs analyzed", f"{(new_ips_considered):,d}")
    table.add_row("New IPs added", f"{(new_ips_added):,d}")
    table.add_row("New ipsum.txt size", f"{(len(ipsum)):,d}")

    print()
    console.print(table)
    args.newips.close()

    return


if __name__ == "__main__":
    pass
