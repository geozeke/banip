#! /usr/bin/env python3

"""Augment the IP addresses in ipsum.txt."""

import sys
from argparse import Namespace
from contextlib import nullcontext
from pathlib import Path
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
            print("Visit https://geozeke.github.io/banip/ for more information.")
            sys.exit(1)

    # Load ipsum.txt.
    msg = status_label("ipsum_load")
    with console.status(msg):
        ipsum = load_ipsum()
    console.print(format_status("ipsum_load"), highlight=False)

    original_ipsum_size = len(ipsum)
    new_ips_considered = 0

    # Start patching.
    msg = status_label("ipsum_patch")
    try:
        input_source = (
            nullcontext(sys.stdin)
            if args.newips == Path("-")
            else args.newips.open("r", encoding="utf-8")
        )
        with input_source as handle, console.status(msg):
            for line in handle:
                parts = line.split()
                try:
                    raw_ip = parts[args.index]
                except IndexError:
                    continue
                if ip := cast(AddressType, extract_ip(raw_ip)):
                    new_ips_considered += 1
                    if (ip not in ipsum) or (ipsum[ip] < args.confidence):
                        ipsum[ip] = args.confidence
    except (OSError, UnicodeError) as exc:
        print(f"Cannot read patch input {args.newips}: {exc}", file=sys.stderr)
        sys.exit(1)
    console.print(format_status("ipsum_patch"), highlight=False)
    new_ips_added = len(ipsum) - original_ipsum_size

    # Update the file on disk.
    IPSUM.write_text(
        render_lines(f"{ip} {hits}" for ip, hits in ipsum.items()),
        encoding="utf-8",
        newline="\n",
    )

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
    return


if __name__ == "__main__":
    pass
