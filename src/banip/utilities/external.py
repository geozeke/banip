"""External service helpers."""

from typing import cast

import requests
from requests.exceptions import RequestException

from banip.constants import AddressType
from banip.utilities.ip import extract_ip


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
