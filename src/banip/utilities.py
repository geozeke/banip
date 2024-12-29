"""Utilities to support file processing."""

import csv
import ipaddress as ipa
import pickle

from rich.console import Console

from banip.constants import COUNTRY_NETS_DICT
from banip.constants import COUNTRY_NETS_TXT
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import AddressType
from banip.constants import NetworkType

# ======================================================================


def split_hybrid(
    hybrid_list: list[AddressType | NetworkType],
) -> tuple[list[AddressType], list[NetworkType]]:
    """Split a heterogeneous list of IPs and Networks.

    Parameters
    ----------
    hybrid_list : list[AddressType  |  NetworkType]
        A list containing a mix of both IPs and/or Networks

    Returns
    -------
    tuple[list[AddressType], list[NetworkType]]
        Two separate, sorted lists in a tuple. The first containing only
        IPs, and the second containing only networks.
    """
    ips = sorted(
        [ip for ip in hybrid_list if isinstance(ip, AddressType)],
        key=lambda x: int(x),
    )
    nets = sorted(
        [net for net in hybrid_list if isinstance(net, NetworkType)],
        key=lambda x: int(x.network_address),
    )
    return ips, nets


# ======================================================================


def compact(
    ip_list: list[AddressType],
    whitelist: list[AddressType | NetworkType],
    min_num: int,
) -> tuple[list[AddressType], list[NetworkType]]:
    """Compact IP addresses into representative Class-C subnets.

    Parameters
    ----------
    ip_list : list[AddressType]
        A list of IP addresses to compact - usually the filtered ipsum
        data.
    whitelist : list[AddressType | NetworkType]
        A list of whitelisted IPs and/or subnets. Need to ensure that a
        collapsed subnet does not include a whitelisted IP and will not
        overlap a whitelisted subnet.
    min_num : int
        The minimum number of IPs required before the group is collapsed
        into a /24 subnet.

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

    # Build a dictionary of subnets for every group of IPs (version 4)
    # in the list.
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
    # groups sized >= min_num. Make sure to check for whitelisted IPs
    # and networks.
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
    """Convert a string to either an IP address or IP subnet.

    Parameters
    ----------
    from_str : str
        This will be a string, representing either an IP address, or IP
        subnet.

    Returns
    -------
    AddressType | NetworkType | None
        The formated ipaddress object.
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
        Return the generated database as a dictionary object to use in
        other parts of the code.
    """
    countries: dict[int, str] = {}
    networks: dict[NetworkType, str] = {}
    console = Console()

    # Lines from the country locations file look like this:
    # 4032283,en,OC,Oceania,TO,Tonga,0
    # There are some country ids in the csv file that reflect continents
    # (e.g. Europe), like this:
    # 6255148,en,EU,Europe,,,0
    # In that case, the two-letter country_ios_code (index 4) is blank,
    # so we need to pull the two-letter continent code from index 2 in
    # the csv file (indices start at 0).
    msg = "Pulling country IDs"
    with console.status(msg):
        with open(GEOLITE_LOC, "r") as f:
            reader = csv.reader(f)
            next(reader)
            for country in reader:
                if not (cic := country[4]):
                    cic = country[2]
                countries[int(country[0])] = cic
    print(f"{msg:.<{PAD}}done")

    # Lines in the IPv4 country blocks file look like this:
    # 1.47.160.0/19,1605651,1605651,,0,0,
    # Lines in the IPv6 country blocks file look like this:
    # 2001:67c:299c::/48,2921044,2921044,,0,0,
    # The variable "net" will hold each line of the file, and the code
    # we're looking for is normally in index 1 (starting from 0). If
    # that entry is blank, use the code in index 2. Index 0 contains the
    # IP address.
    msg = "Geotagging Networks"
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
    print(f"{msg:.<{PAD}}done")

    msg = "Generating build products"
    with console.status(msg):
        _, keys = split_hybrid(list(networks.keys()))
        with open(COUNTRY_NETS_TXT, "w") as f:
            for key in keys:
                f.write(f"{format(key)} {networks[key]}\n")
        with open(COUNTRY_NETS_DICT, "wb") as f:
            pickle.dump(networks, f)
    print(f"{msg:.<{PAD}}done")

    return networks


# ======================================================================


def ip_in_network(
    ip: AddressType, networks: list[NetworkType], first: int, last: int
) -> NetworkType | None:
    """Check if a single IP is in a list of networks.

    This is a recursive binary search across a sorted list of
    heterogeneous networks (IPv4, IPv6 or both) to see if a single IP
    address is contained in any of the networks.

    Parameters
    ----------
    ip : AddressType
        Either an IPv4 or IPv6 address.
    networks : list[NetworkType]
        A sorted heterogeneous list of networks.
    first : int
        The starting index in the binary search.
    last : int
        The ending index in the binary search.

    Returns
    -------
    NetworkType | None
        If IP is in one of the networks in the list, then return the
        network containing it; if not, return None.
    """
    if first > last:
        return None

    mid = (first + last) // 2
    ip_int = int(ip)
    inner = int(networks[mid].network_address)
    outer = int(networks[mid].broadcast_address)

    if ip_int >= inner and ip_int <= outer:
        return networks[mid]
    if ip_int < inner:
        return ip_in_network(ip, networks, first, mid - 1)
    return ip_in_network(ip, networks, mid + 1, last)


# ======================================================================


def load_ipsum() -> dict[AddressType, int]:
    """Load the ipsum.txt file into a dictionary.

    Returns
    -------
    dict[AddressType, int]
        The ipsum.txt file loaded into a dictionary.
    """
    with open(IPSUM, "r") as f:
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


def load_rendered_blacklist() -> tuple[list[AddressType], list[NetworkType]]:
    """Load the contents of the rendered blacklist

    Separate it into separate, sorted lists of Networks and IPs

    Returns
    -------
    tuple[list[NetworkType], list[AddressType]]
        The rendered blacklist split into Networks and IPs
    """
    with open(RENDERED_BLACKLIST, "r") as f:
        rendered = [token for line in f if (token := extract_ip(line.strip()))]
    return split_hybrid(rendered)
