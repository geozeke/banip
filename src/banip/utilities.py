"""Utilities to support file processing."""

import csv
import ipaddress as ipa
import textwrap
from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path

from banip.constants import COUNTRY_NETS
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import PAD
from banip.constants import AddressType
from banip.constants import NetworkType

# ======================================================================


def wrap_tight(msg: str, columns=70) -> str:
    """Clean up a multi-line docstring.

    Take a multi-line docstring and wrap it cleanly as a paragraph to a
    specified column width.

    Parameters
    ----------
    msg : str
        The docstring to be wrapped.
    columns : int, optional
        Column width for wrapping, by default 70.

    Returns
    -------
    str
        A wrapped paragraph.
    """
    clean = " ".join([t for token in msg.split("\n") if (t := token.strip())])
    return textwrap.fill(clean, width=columns)


# ======================================================================


def extract_ip(from_str: str) -> AddressType | NetworkType | None:
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
    to_ip: AddressType | NetworkType | None = None
    try:
        if "/" in from_str:
            to_ip = ipa.ip_network(from_str)
        else:
            to_ip = ipa.ip_address(from_str)
    except ValueError:
        return None
    return to_ip


# ======================================================================


def tag_networks() -> dict[NetworkType, str]:
    """Create the haproxy_geo_ip.txt database.

    This will create a HAProxy-friendly file of global subnets and their
    associated two-letter country codes.
    """
    countries: dict[int, str] = {}
    networks: dict[NetworkType, str] = {}

    # Lines from the country locations file look like this:
    # 4032283,en,OC,Oceania,TO,Tonga,0
    # There are some country ids in the csv file that reflect continents
    # (e.g. Europe), like this:
    # 6255148,en,EU,Europe,,,0
    # In that case, the two-letter country_ios_code (index 4) is blank,
    # so we need to pull the two-letter continent code from index 2 in
    # the csv file (indices start at 0).
    print(f"{'Pulling country IDs':.<{PAD}}", end="", flush=True)
    with open(GEOLITE_LOC, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for country in reader:
            if not (cic := country[4]):
                cic = country[2]
            countries[int(country[0])] = cic
    print("done")

    # Lines in the IPv4 country blocks file look like this:
    # 1.47.160.0/19,1605651,1605651,,0,0,
    # The variable "net" will hold each line of the file, and the code
    # we're looking for is normally in index 1 (starting from 0). If
    # that entry is blank, use the code in index 2. Index 0 contains the
    # IP address.
    print(f"{'Geotagging IPv4 Networks':.<{PAD}}", end="", flush=True)
    with open(GEOLITE_4, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for net in reader:
            try:
                country_id = countries[int(net[1])]
            except ValueError:
                country_id = countries[int(net[2])]
            networks[ipa.IPv4Network(net[0])] = country_id
    print("done")

    # Lines in the IPv6 country blocks file look like this:
    # 2001:67c:299c::/48,2921044,2921044,,0,0,
    # The variable "net" will hold each line of the file, and the code
    # we're looking for is normally in index 1 (starting from 0). If
    # that entry is blank, use the code in index 2. Index 0 contains the
    # IP address.
    print(f"{'Geotagging IPv6 Networks':.<{PAD}}", end="", flush=True)
    with open(GEOLITE_6, "r") as f:
        reader = csv.reader(f)
        next(reader)
        for net in reader:
            try:
                country_id = countries[int(net[1])]
            except ValueError:
                country_id = countries[int(net[2])]
            networks[ipa.IPv6Network(net[0])] = country_id
    print("done")

    print(f"{'Generating build products':.<{PAD}}", end="", flush=True)
    keys = sorted(list(networks.keys()), key=lambda x: int(x.network_address))
    with open(COUNTRY_NETS, "w") as f:
        for key in keys:
            f.write(f"{format(key)} {networks[key]}\n")
    print("done")

    return networks


# ======================================================================


def ip_in_network(
    ip: IPv4Address | IPv6Address,
    networks: list[IPv4Network | IPv6Network],
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
    ip_int = int(ip)
    network_address = int(networks[mid].network_address)
    broadcast_address = int(networks[mid].broadcast_address)
    if ip_int >= network_address and ip_int <= broadcast_address:
        return True
    if ip_int < network_address:
        return ip_in_network(ip, networks, first, mid - 1)
    return ip_in_network(ip, networks, mid + 1, last)


# ======================================================================


def load_ipsum(ipsum_file: Path) -> dict[AddressType, int]:
    """Load the ipsum.txt file into a dictionary.

    Parameters
    ----------
    ipsum_file : Path
        pathlib Path object pointing to the ipsum.txt file.

    Returns
    -------
    dict[AddressType, int]
        The ipsum.txt file loaded into a dictionary.
    """
    with open(ipsum_file, "r") as f:
        ipsum: dict[AddressType, int] = {}
        for line in f:
            parts = line.strip().split()
            try:
                ip = ipa.ip_address(parts[0])
                hits = int(parts[1])
            except (ValueError, NameError):
                continue
            ipsum[ip] = hits
    return ipsum
