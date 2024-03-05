"""Docstring."""

import ipaddress as ipa
import os
from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path

from tqdm import tqdm  # type: ignore


def clear() -> None:
    """Clear the screen.

    OS-agnostic version, which will work with both Windows and Linux.
    """
    os.system("clear" if os.name == "posix" else "cls")


def filter_networks(
    fname: str | Path,
    countries: list[str],
) -> list[IPv4Network | IPv6Network]:
    """Do this."""
    networks_L: list[IPv4Network | IPv6Network] = []
    with open(fname, "r") as f:
        lines = len(f.readlines())
        f.seek(0)
        for line in tqdm(
            f,
            desc="Lines",
            total=lines,
            colour="#bf80f2",
            unit="lines",
        ):
            if (clean := line.strip()) and clean[0] != "#":
                parts = clean.split()
                if parts[1] in countries:
                    networks_L.append(ipa.ip_network(parts[0], strict=False))
    return networks_L


def filter_addresses(
    fname: str | Path,
    min_hits: int,
) -> list[IPv4Address | IPv6Address]:
    """Do this."""
    ip_L: list[IPv4Address | IPv6Address] = []
    with open(fname, "r") as f:
        lines = len(f.readlines())
        f.seek(0)
        for line in tqdm(
            f,
            desc="Lines",
            total=lines,
            colour="#bf80f2",
            unit="lines",
        ):
            if (clean := line.strip()) and clean[0] != "#":
                parts = clean.split()
                if int(parts[1]) >= min_hits:
                    ip_L.append(ipa.ip_address(parts[0]))
    return ip_L
