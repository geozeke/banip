"""Utilities to support file processing."""

import ipaddress as ipa
import os
from ipaddress import IPv4Address
from ipaddress import IPv4Network
from pathlib import Path
from typing import Any

from tqdm import tqdm  # type: ignore


def clear() -> None:
    """Clear the screen.

    OS-agnostic version, which will work with both Windows and Linux.
    """
    os.system("clear" if os.name == "posix" else "cls")


def filter(fname: str | Path, metric: list[str] | int) -> list[Any]:
    """Filter items from lists of networks or IP addresses.

    Parameters
    ----------
    fname : str | Path
        The file containing country subnets or IP addresses.
    metric : list[str] | int
        Either a list of target countries to filter, or a target
        threshold for IP address filtering. Each banned ip address in
        the source database has a factor (from 1 to 10) indicating a
        level of certainty that the ip address is a malicious actor. The
        default threshold used is 3. Anything less than that may result
        in false positives and increases the time required to generate
        the list. You may choose any threshold from 1 to 10, but I
        recommend not going lower than 3.

    Returns
    -------
    list[Any]
        A list of IP subnets based on target countries, or a list of IP
        addresses based on confidence thresholds.
    """
    bag: list[Any] = []
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
                if type(metric) is list:
                    if parts[1] in metric:
                        bag.append(
                            ipa.ip_network(
                                parts[0],
                                strict=False,
                            )
                        )
                elif type(metric) is int:
                    if int(parts[1]) >= metric:
                        bag.append(ipa.ip_address(parts[0]))

    return bag


def split46(bag_of_stuff: list[Any]) -> tuple[list[Any], list[Any]]:
    """Split a list of tokens into two lists, based on protocol.

    Tokens will either be IPv4/6 Addresses, or IPv4/6 subnets.

    Parameters
    ----------
    bag_of_stuff : list[Any]
        This will contain either a mix of IP addresses (v4/v6) or a mix
        of subnets (v4/v6). A single input will contain either all IP
        addresses or all subnets, but not a mix of both.

    Returns
    -------
    tuple[list[Any], list[Any]]
        The input split into two separate lists, with v4 protocol first
        and v6 protocol second.
    """
    bag4: list[Any] = []
    bag6: list[Any] = []
    for item in bag_of_stuff:
        if type(item) is IPv4Address or type(item) is IPv4Network:
            bag4.append(item)
        else:
            bag6.append(item)
    return bag4, bag6
