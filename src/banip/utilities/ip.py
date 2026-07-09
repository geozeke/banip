"""IP parsing and rendering helpers."""

import ipaddress as ipa
from collections.abc import Iterable

from banip.constants import AddressType
from banip.constants import AddressTypes
from banip.constants import NetworkType
from banip.constants import NetworkTypes


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


def render_lines(items: Iterable[object]) -> str:
    """Render items as newline-terminated text lines.

    Parameters
    ----------
    items : Iterable[object]
        Items to convert to text.

    Returns
    -------
    str
        One newline-terminated line per item, or an empty string for an
        empty iterable.
    """
    return "".join(f"{item}\n" for item in items)


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
