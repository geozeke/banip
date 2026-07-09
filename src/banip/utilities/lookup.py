"""Network lookup and compaction helpers."""

import ipaddress as ipa
from collections.abc import Iterable
from dataclasses import dataclass

from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities.ip import split_hybrid


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

    if min_num == 0:
        return sorted(ip_list, key=lambda x: int(x)), []

    for ip in ip_list:
        if ip.version != 4:
            leftovers.append(ip)
            continue
        network = ipa.ip_network(f"{ip}/24", strict=False)
        if network in D:
            D[network].add(ip)
        else:
            D[network] = {ip}

    for net, ips in D.items():
        if (
            len(ips) >= min_num
            and not any([ip in net for ip in white_ips])
            and not any([white_net.overlaps(net) for white_net in white_nets])
        ):
            compacted.append(net)
        else:
            compacted += list(ips)

    return split_hybrid(compacted + leftovers)


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
