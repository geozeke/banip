"""Utilities to support file processing."""

import csv
import ipaddress as ipa
import os
from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Network
from pathlib import Path
from typing import Any

from tqdm import tqdm  # type: ignore

from banip.contants import BANNED_IPS
from banip.contants import COUNTRY_NETS
from banip.contants import GEOLITE_4
from banip.contants import GEOLITE_6
from banip.contants import GEOLITE_LOC
from banip.contants import RENDERED_BLACKLIST

# ===============================================================


def clear() -> None:
    """Clear the screen.

    OS-agnostic version, which will work with both Windows and Linux.
    """
    os.system("clear" if os.name == "posix" else "cls")


# ===============================================================


def extract_ip(from_str: str) -> Any:
    """Convert a string to either an IP address or IP subnet.

    Parameters
    ----------
    from_str : str
        This will be a string, representing either an IP address, or IP
        subnet.

    Returns
    -------
    Any
        This will be one of four types: IPv4Address | IPv6Address |
        IPv4Network | IPv6Network.
    """
    to_ip: Any = None
    if "/" in from_str:
        try:
            to_ip = ipa.ip_network(from_str)
        except AttributeError:
            return None
    else:
        try:
            to_ip = ipa.ip_address(from_str)
        except AttributeError:
            return None
    return to_ip


# ===============================================================


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


# ===============================================================


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


# ===============================================================


def tag_networks() -> None:
    """Create the haproxy_geo_ip.txt database.

    This will create a HAProxy-friendly file of global subnets and their
    associated two-letter country codes.
    """
    countries_D: dict[int, str] = {}
    ipv4_D: dict[IPv4Network, str] = {}
    ipv6_D: dict[IPv6Network, str] = {}

    print("Pulling country IDs")
    with open(GEOLITE_LOC, "r") as f:
        lines = len(f.readlines()) - 1
        f.seek(0)
        reader = csv.reader(f)
        next(reader)
        for country in tqdm(
            reader,
            desc="Countries",
            total=lines,
            colour="#bf80f2",
            unit="countries",
        ):
            # Lines from the country locations file look like this:
            # 4032283,en,OC,Oceania,TO,Tonga,0
            # There are some country ids in the csv file that reflect
            # continents (e.g. Europe), like this:
            # 6255148,en,EU,Europe,,,0
            # In that case, the two-letter country_ios_code (index 4) is
            # blank, so we need to pull the two-letter continent code
            # from index 2 in the csv file (indices start at 0).
            if not (cic := country[4]):
                cic = country[2]
            countries_D[int(country[0])] = cic

    print("\nGeotagging IPv4 Networks")
    with open(GEOLITE_4, "r") as f:
        lines = len(f.readlines()) - 1
        f.seek(0)
        reader = csv.reader(f)
        next(reader)
        for net in tqdm(
            reader,
            desc="IPv4 Networks",
            total=lines,
            colour="#bf80f2",
            unit="nets",
        ):
            # Lines in the IPv4 country blocks file look like this:
            # 1.47.160.0/19,1605651,1605651,,0,0,
            # The variable "net" will hold each line of the file, and
            # the code we're looking for is normally in index 1
            # (starting from 0). If that entry is blank, use the code in
            # index 2. Index 0 contains the IP address.
            try:
                country_id = countries_D[int(net[1])]
            except ValueError:
                country_id = countries_D[int(net[2])]
            ipv4_D[ipa.IPv4Network(net[0])] = country_id

    print("\nGeotagging IPv6 Networks")
    with open(GEOLITE_6, "r") as f:
        lines = len(f.readlines()) - 1
        f.seek(0)
        reader = csv.reader(f)
        next(reader)
        for net in tqdm(
            reader,
            desc="IPv6 Networks",
            total=lines,
            colour="#bf80f2",
            unit="nets",
        ):
            # Lines in the IPv6 country blocks file look like this:
            # 2001:67c:299c::/48,2921044,2921044,,0,0,
            # The variable "net" will hold each line of the file, and
            # the code we're looking for is normally in index 1
            # (starting from 0). If that entry is blank, use the code in
            # index 2. Index 0 contains the IP address.
            try:
                country_id = countries_D[int(net[1])]
            except ValueError:
                country_id = countries_D[int(net[2])]
            ipv6_D[ipa.IPv6Network(net[0])] = country_id

    print("\nGenerating interim build products...", end="")
    keys_4 = list(ipv4_D.keys())
    keys_6 = list(ipv6_D.keys())
    keys_4.sort()
    keys_6.sort()
    key: IPv4Network | IPv6Network
    with open(COUNTRY_NETS, "w") as f:
        for key in keys_4:
            f.write(f"{format(key)} {ipv4_D[key]}\n")
        for key in keys_6:
            f.write(f"{format(key)} {ipv6_D[key]}\n")
    print("Done\n")


# ===============================================================


def check_ip(ip: str) -> None:
    """Display available data for a particular IP address.

    Parameters
    ----------
    ip : str
        IPv4 or IPv address of interest.
    """
    try:
        ipa.ip_address(ip)
    except ValueError:
        print(f"{ip} is not a valid IP address.")
        return

    print()
    found = False
    if RENDERED_BLACKLIST.exists():
        with open(RENDERED_BLACKLIST, "r") as f:
            for line in f:
                if ip in line:
                    source = RENDERED_BLACKLIST.name
                    print(f"{ip} found in {source}")
                    found = True
                    break

    if BANNED_IPS.exists():
        with open(BANNED_IPS, "r") as f:
            for line in f:
                if ip in line:
                    source = BANNED_IPS.name
                    hitcount = line.split()[1]
                    print(f"{ip} found in {source} with {hitcount} hits.")
                    found = True
                    break

    if not found:
        print(f"{ip} not found.")

    return


# ===============================================================


def ip_in_network(
    ip: Any,
    networks: list[Any],
    first: int,
    last: int,
) -> bool:
    """Check if a single IP is in a list of networks.

    This is a recursive binary search across a list of networks (either
    all IPv4 or all IPv6) to see if a single IP address is contained in
    any of the networks.

    Parameters
    ----------
    ip : Any
        This will be either an IPv4 or IPv6 address, in ip_address()
        format.
    networks : list[Any]
        This is a homogenous list of networks. The type of items in the
        list with be either IPv4Network or IPv6Network.
    first : int
        The starting index in the binary search.
    last : int
        The ending index in the binary search.

    Returns
    -------
    bool
        True if ip is in any of the networks in the list; False
        otherwise.
    """
    if first > last:
        return False
    mid = (first + last) // 2
    clients = ipa.ip_network(networks[mid])
    if ip in clients:
        return True
    if ip < clients[0]:
        return ip_in_network(ip, networks, first, mid - 1)
    return ip_in_network(ip, networks, mid + 1, last)
