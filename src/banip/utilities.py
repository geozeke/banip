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
    """Pull networks for target countries.

    Parameters
    ----------
    fname : str | Path
        The name of the data file containing subnets for each country
        (e.g. haproxy_geo_ip.txt)
    countries : list[str]
        A list of target countries (expressed as two-letter codes)

    Returns
    -------
    list[IPv4Network | IPv6Network]
        All subnets for the target countries.
    """
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
    """Filter banned IP addresses based on hit counts.

    Each banned ip address in the source database has a factor
    (from 1 to 10) indicating a level of certainty that the ip address
    is a malicious actor. The default threshold used is 3. Anything
    less than that may result in false positives and increases the time
    required to generate the list. You may choose any threshold from 1
    to 10, but I recommend not going lower than 3.

    Parameters
    ----------
    fname : str | Path
        The file from containing malicious IPs, with associated hit
        counts.
    min_hits : int
        The threshold hit count for filtering IP addresses.

    Returns
    -------
    list[IPv4Address | IPv6Address]
        A list of IP address with hit counts >= min_hits.
    """
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
