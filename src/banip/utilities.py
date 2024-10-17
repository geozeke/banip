"""Utilities to support file processing."""

import csv
import ipaddress as ipa
import textwrap
from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path
from typing import Any

from tqdm import tqdm

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


def custom_sort(
    collection: list[AddressType | NetworkType] | set[AddressType | NetworkType],
) -> list[AddressType | NetworkType]:
    """Create a custom sorting of a heterogenous collection of IPTypes.

    Parameters
    ----------
    collection : list[IPType] | set[IPType]
        A collection of objects to be sorted.

    Returns
    -------
    list[IPType]
        A list that is sorted, with the IP addresses first, followed by
        Subnets.
    """
    # Split addresses and networks so we can stack them separately.
    addresses = [token for token in collection if isinstance(token, AddressType)]
    networks = [token for token in collection if isinstance(token, NetworkType)]
    addresses = sorted(addresses, key=lambda x: int(x))
    networks = sorted(networks, key=lambda x: int(x.network_address))
    return addresses + networks


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


def filter(fname: Path, metric: list[str] | int) -> list[Any]:
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
    tokens: list[Any] = []
    with open(fname, "r") as f:
        lines = len(f.readlines())
        f.seek(0)
        for line in tqdm(
            f,
            desc="  Total lines",
            total=lines,
            colour="#bf80f2",
            unit="lines",
        ):
            if (clean := line.strip()) and clean[0] != "#":
                parts = clean.split()
                if type(metric) is list:
                    if parts[1] in metric:
                        tokens.append(
                            ipa.ip_network(
                                parts[0],
                                strict=False,
                            )
                        )
                elif type(metric) is int:
                    if int(parts[1]) >= metric:
                        tokens.append(ipa.ip_address(parts[0]))

    return tokens


# ======================================================================


def split46(tokens: list[Any]) -> tuple[list[Any], list[Any]]:
    """Split a list of tokens into two lists, based on protocol.

    Tokens will either be IPv4/6 Addresses, or IPv4/6 subnets.

    Parameters
    ----------
    tokens : list[Any]
        This will contain either a mix of IP addresses (v4/v6) or a mix
        of subnets (v4/v6). A single input will contain either all IP
        addresses or all subnets, but not a mix of both.

    Returns
    -------
    tuple[list[Any], list[Any]]
        The input split into two separate lists, with v4 protocol first
        and v6 protocol second.
    """
    tokens4: list[Any] = []
    tokens6: list[Any] = []
    for item in tokens:
        if type(item) is IPv4Address or type(item) is IPv4Network:
            tokens4.append(item)
        else:
            tokens6.append(item)

    return tokens4, tokens6


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


def load_dictionary(target_file: Path) -> dict[str, list[Any]] | None:
    """Load and return a dictionary of IP objects.

    This will process the given file return a dictionary with individual
    lists of: IPv4Addresses, IPv6Addresses, IPv4Networks, IPv6Networks.
    The dictionary keys are:

    V4A: IPv4 Addresses.
    V6A: IPv6 Addresses.
    V4N: IPv4 Subnets.
    V6N: IPv6 Subnets.

    Parameters
    ----------
    target_file : str | Path
        File to be processed

    Returns
    -------
    dict[str, list[Any]] | None
        A dictionary of ipaddress-type objects. If the target_file does
        not exist, then return None.
    """
    # Strategically name the dictionary keys, so we can extract them
    # from the type information of each token as we process it.
    D: dict[str, list[Any]] = {
        "V4A": [],
        "V6A": [],
        "V4N": [],
        "V6N": [],
    }
    if not target_file.exists():
        return None
    token: Any = None
    with open(target_file, "r") as f:
        for line in f:
            if not (token := extract_ip(line.strip())):
                continue
            D[f"V{str(type(token))[-10:-8]}"].append(token)
    return D
