"""Utilities to support file processing."""

import csv
import ipaddress as ipa
import os
import pickle
from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast

import requests
from requests.exceptions import RequestException
from rich.console import Console

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import COUNTRY_NETS_TXT
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import RENDERED_BLACKLIST
from banip.constants import AddressType
from banip.constants import AddressTypes
from banip.constants import NetworkType
from banip.constants import NetworkTypes

# ======================================================================


def print_docstring(msg: str) -> None:
    """Print a formatted docstring.

    This function assumes the docstring is in a very specific format:

    >>> msg = \"\"\"
    >>> First line (non-blank)
    >>>
    >>> Subsequent lines
    >>> Subsequent lines
    >>> Subsequent lines
    >>> ...
    >>> Can include empty lines after the first.
    >>> \"\"\"

    Parameters
    ----------
    msg : str
        The docstring to be printed.
    """
    # Delete the first line ('\n' by itself), remove any leading padding
    # from the string, then print.
    lines = msg.split("\n")[1:]
    spaces = 0
    for c in lines[0]:
        if c.isspace():
            spaces += 1
        else:
            break
    formatted_docstring = "\n".join([line[spaces:] for line in lines])
    print(formatted_docstring)
    return


# ======================================================================


@dataclass(frozen=True)
class StatusMessages:
    """Registry for keyed progress messages."""

    labels: dict[str, str]

    @property
    def max_label_length(self) -> int:
        """Return the length of the longest registered label."""
        return max(len(label) for label in self.labels.values())

    def label(self, key: str, **kwargs: object) -> str:
        """Return a formatted status label.

        Parameters
        ----------
        key : str
            Key for the registered status label.
        **kwargs : object
            Values used to format dynamic labels.

        Returns
        -------
        str
            The formatted status label.
        """
        return self.labels[key].format(**kwargs)

    def format(self, key: str, status: str = "✅", **kwargs: object) -> str:
        """Format a status line with aligned status values.

        Parameters
        ----------
        key : str
            Key for the registered status label.
        status : str, optional
            The status value. Defaults to a check mark.
        **kwargs : object
            Values used to format dynamic labels.

        Returns
        -------
        str
            The formatted status line.
        """
        label = self.label(key, **kwargs)
        target_length = max(self.max_label_length, len(label))
        leader = "." * max(target_length - len(label) + 3, 3)
        return f"{label}{leader}{status}"


STATUS_MESSAGES = StatusMessages(
    {
        "analyze": "Analyzing",
        "blacklist_rendered_load": "Loading rendered blacklist",
        "build_products": "Generating build products",
        "country_filter": "Filtering networks",
        "custom_prune": "Pruning custom blacklist",
        "geolite_load": "Loading geolocation data",
        "geo_pull": "Pulling country IDs",
        "geo_tag": "Geotagging networks",
        "ipsum_compact": "Compacting ipsum ({compact})",
        "ipsum_load": "Loading ipsum.txt",
        "ipsum_load_data": "Loading ipsum data",
        "ipsum_patch": "Patching with new IP addresses",
        "ipsum_prune": "Pruning ipsum.txt",
        "lists_render": "Rendering lists",
        "redundant_remove": "Removing redundant IP addresses",
        "repack": "Repackaging custom IP addresses",
        "stats_load": "Loading data",
    }
)


def status_label(key: str, **kwargs: object) -> str:
    """Return a status label by key.

    Parameters
    ----------
    key : str
        Key for the registered status label.
    **kwargs : object
        Values used to format dynamic labels.

    Returns
    -------
    str
        The formatted status label.
    """
    return STATUS_MESSAGES.label(key, **kwargs)


def format_status(key: str, status: str = "✅", **kwargs: object) -> str:
    """Format a status line with a minimum dot leader.

    Parameters
    ----------
    key : str
        Key for the registered status label.
    status : str, optional
        The status value. Defaults to a check mark.
    **kwargs : object
        Values used to format dynamic labels.

    Returns
    -------
    str
        The formatted status line.
    """
    return STATUS_MESSAGES.format(key, status, **kwargs)


# ======================================================================


def split_hybrid(
    hybrid_list: Iterable[AddressType | NetworkType],
) -> tuple[list[AddressType], list[NetworkType]]:
    """Split a mixed list of IP addresses and networks.

    Parameters
    ----------
    hybrid_list : Iterable[AddressType  |  NetworkType]
        IP addresses, networks, or both.

    Returns
    -------
    tuple[list[AddressType], list[NetworkType]]
        A tuple of sorted lists. The first list contains IP addresses,
        and the second list contains networks.
    """
    ips = sorted(
        [ip for ip in hybrid_list if isinstance(ip, AddressTypes)],
        key=lambda x: int(x),
    )
    nets = sorted(
        [net for net in hybrid_list if isinstance(net, NetworkTypes)],
        key=lambda x: int(x.network_address),
    )
    return ips, nets


# ======================================================================


@dataclass(frozen=True)
class NetworkBounds:
    """Precomputed integer bounds for one IP network.

    Parameters
    ----------
    first : int
        The first address in the network as an integer.
    last : int
        The last address in the network as an integer.
    network : NetworkType
        The original network object.
    """

    first: int
    last: int
    network: NetworkType


@dataclass(frozen=True)
class NetworkLookup:
    """Lookup-ready network bounds split by address family.

    Parameters
    ----------
    ipv4 : tuple[NetworkBounds, ...]
        IPv4 network bounds sorted by starting address.
    ipv6 : tuple[NetworkBounds, ...]
        IPv6 network bounds sorted by starting address.
    """

    ipv4: tuple[NetworkBounds, ...]
    ipv6: tuple[NetworkBounds, ...]


def build_network_lookup(networks: Iterable[NetworkType]) -> NetworkLookup:
    """Precompute integer bounds for network membership checks.

    Parameters
    ----------
    networks : Iterable[NetworkType]
        Networks to include in the lookup.

    Returns
    -------
    NetworkLookup
        Network bounds split by address family and sorted by starting
        address.
    """
    ipv4: list[NetworkBounds] = []
    ipv6: list[NetworkBounds] = []

    for network in networks:
        bounds = NetworkBounds(
            first=int(network.network_address),
            last=int(network.broadcast_address),
            network=network,
        )
        if network.version == 4:
            ipv4.append(bounds)
        else:
            ipv6.append(bounds)

    return NetworkLookup(
        ipv4=tuple(sorted(ipv4, key=lambda x: x.first)),
        ipv6=tuple(sorted(ipv6, key=lambda x: x.first)),
    )


# ======================================================================


def compact(
    ip_list: list[AddressType],
    whitelist: Iterable[AddressType | NetworkType],
    min_num: int,
) -> tuple[list[AddressType], list[NetworkType]]:
    """Compact IP addresses into representative /24 subnets.

    Parameters
    ----------
    ip_list : list[AddressType]
        A list of IP addresses to compact, usually the filtered ipsum
        data.
    whitelist : Iterable[AddressType | NetworkType]
        Whitelisted IP addresses, networks, or both. A compacted subnet
        must not include a whitelisted IP address or overlap a
        whitelisted network.
    min_num : int
        The minimum number of IP addresses required before the group is
        collapsed into a /24 subnet.

    Returns
    -------
    tuple[list[AddressType], list[NetworkType]]
        Separate lists of IP addresses and /24 subnets.
    """
    compacted: list[AddressType | NetworkType] = []
    leftovers: list[AddressType | NetworkType] = []
    D: dict[NetworkType, set[AddressType]] = {}
    white_ips, white_nets = split_hybrid(whitelist)

    # 0 indicates no compaction desired. Return the original list,
    # sorted.
    if min_num == 0:
        return sorted(ip_list, key=lambda x: int(x)), []

    # Build a dictionary of subnets for every group of IPv4 addresses in
    # the list.
    for ip in ip_list:
        if ip.version != 4:
            leftovers.append(ip)
            continue
        network = ipa.ip_network(f"{ip}/24", strict=False)
        if network in D:
            D[network].add(ip)
        else:
            D[network] = {ip}

    # Create a new hybrid list representing IP addresses for groups
    # containing less than the min_num of members, and /24 subnets for
    # groups sized >= min_num. Make sure to check for whitelisted IP
    # addresses and networks.
    for net, ips in D.items():
        if (
            len(ips) >= min_num
            and not any([ip in net for ip in white_ips])
            and not any([white_net.overlaps(net) for white_net in white_nets])
        ):
            compacted.append(net)
        else:
            compacted += list(ips)

    # Return separate, sorted lists of IP addresses and subnets.
    return split_hybrid(compacted + leftovers)


# ======================================================================


def extract_ip(from_str: str) -> AddressType | NetworkType | None:
    """Convert a string to an IP address or IP network.

    Parameters
    ----------
    from_str : str
        A string representing an IP address or IP network.

    Returns
    -------
    AddressType | NetworkType | None
        The parsed IP address or network, or None if parsing fails.
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
    """Generate the haproxy_geo_ip.txt database.

    This will create a HAProxy-friendly file of global subnets and their
    associated two-letter country codes.

    Returns
    -------
    dict[NetworkType, str]
        The generated database as a dictionary for reuse by other
        commands.
    """
    countries: dict[int, str] = {}
    networks: dict[NetworkType, str] = {}
    console = Console()

    # Lines from the country locations file look like this:
    # 4032283,en,OC,Oceania,TO,Tonga,0
    # There are some country IDs in the CSV file that reflect continents
    # (e.g. Europe), like this:
    # 6255148,en,EU,Europe,,,0
    # In that case, the two-letter country ISO code (index 4) is blank,
    # so we need to pull the two-letter continent code from index 2 in
    # the CSV file (indices start at 0).
    msg = status_label("geo_pull")
    with console.status(msg):
        with open(GEOLITE_LOC, "r") as f:
            reader = csv.reader(f)
            next(reader)
            for country in reader:
                if not (cic := country[4]):
                    cic = country[2]
                countries[int(country[0])] = cic
    print(format_status("geo_pull"))

    # Lines in the IPv4 country blocks file look like this:
    # 1.47.160.0/19,1605651,1605651,,0,0,
    # Lines in the IPv6 country blocks file look like this:
    # 2001:67c:299c::/48,2921044,2921044,,0,0,
    # The variable "net" will hold each line of the file, and the code
    # we're looking for is normally in index 1 (starting from 0). If
    # that entry is blank, use the code in index 2. Index 0 contains the
    # IP address.
    msg = status_label("geo_tag")
    with console.status(msg):
        for geolite_file in [GEOLITE_4, GEOLITE_6]:
            with open(geolite_file, "r") as f:
                reader = csv.reader(f)
                next(reader)
                for net in reader:
                    try:
                        country_id = countries[int(net[1])]
                    except ValueError:
                        country_id = countries[int(net[2])]
                    networks[ipa.ip_network(net[0])] = country_id
    print(format_status("geo_tag"))

    msg = status_label("build_products")
    with console.status(msg):
        _, keys = split_hybrid(list(networks.keys()))
        with open(COUNTRY_NETS_TXT, "w") as f:
            for key in keys:
                f.write(f"{format(key)} {networks[key]}" + "\n")
        with open(COUNTRY_NETS_DICT, "wb") as f:
            pickle.dump(networks, f)
    print(format_status("build_products"))

    return networks


# ======================================================================


def ip_in_network(ip: AddressType, lookup: NetworkLookup) -> NetworkType | None:
    """Check whether a single IP address is in a network lookup.

    This is an iterative binary search across precomputed integer
    network bounds for the address family of the target IP address.

    Parameters
    ----------
    ip : AddressType
        Either an IPv4 or IPv6 address.
    lookup : NetworkLookup
        Lookup-ready network bounds.

    Returns
    -------
    NetworkType | None
        The network containing the IP address, or None if no network
        contains it.
    """
    networks = lookup.ipv4 if ip.version == 4 else lookup.ipv6
    first = 0
    last = len(networks) - 1
    ip_int = int(ip)

    while first <= last:
        mid = (first + last) // 2
        bounds = networks[mid]

        if ip_int >= bounds.first and ip_int <= bounds.last:
            return bounds.network
        if ip_int < bounds.first:
            last = mid - 1
        else:
            first = mid + 1

    return None


# ======================================================================


def load_ipsum() -> dict[AddressType, int]:
    """Load the ipsum.txt file into a dictionary.

    Returns
    -------
    dict[AddressType, int]
        The contents of ipsum.txt as a dictionary.
    """
    with open(IPSUM, "r") as f:
        ipsum: dict[AddressType, int] = {}
        for line in f:
            parts = line.strip().split()
            try:
                ip = ipa.ip_address(parts[0])
                hits = int(parts[1])
            except (IndexError, ValueError):
                continue
            ipsum[ip] = hits

    return ipsum


# ======================================================================


def load_rendered_blacklist() -> tuple[list[AddressType], list[NetworkType]]:
    """Load the contents of the rendered blacklist.

    Separate it into sorted lists of IP addresses and networks.

    Returns
    -------
    tuple[list[AddressType], list[NetworkType]]
        The rendered blacklist split into IP addresses and networks.
    """
    with open(RENDERED_BLACKLIST, "r") as f:
        rendered = [token for line in f if (token := extract_ip(line.strip()))]
    return split_hybrid(rendered)


# ======================================================================


def get_public_ip() -> AddressType | None:
    """Return the public IP address of the host.

    Returns
    -------
    AddressType | None
        The public-facing IPv4 or IPv6 address of the host, or None if
        the request fails or the response cannot be parsed as an IP
        address.

    Raises
    ------
    RequestException
        If the connection to the AWS server fails.
    """
    try:
        response = requests.get("https://checkip.amazonaws.com")
        response.raise_for_status()
        if public_ip := extract_ip(from_str=response.text.strip()):
            return cast(AddressType, public_ip)
        else:
            return None
    except RequestException:
        return None


# ======================================================================


def clear() -> None:
    """Clear the screen.

    This is an OS-agnostic version, which works with both Windows
    and Linux.
    """
    os.system("clear" if os.name == "posix" else "cls")


# ======================================================================
