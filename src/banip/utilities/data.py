"""Data-file loading and generation helpers."""

import csv
import ipaddress as ipa
import mmap
from pathlib import Path

from rich.console import Console

from banip.constants import COUNTRY_NETS_TXT
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import RENDERED_BLOCKLIST
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities.display import format_status
from banip.utilities.display import status_label
from banip.utilities.ip import extract_ip
from banip.utilities.ip import render_lines
from banip.utilities.ip import split_hybrid


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

    msg = status_label("geo_pull")
    with console.status(msg):
        with GEOLITE_LOC.open("r") as f:
            reader = csv.reader(f)
            next(reader)
            for country in reader:
                if not (cic := country[4]):
                    cic = country[2]
                countries[int(country[0])] = cic
    print(format_status("geo_pull"))

    msg = status_label("geo_tag")
    with console.status(msg):
        for geolite_file in [GEOLITE_4, GEOLITE_6]:
            with geolite_file.open("r") as f:
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
        keys = sorted(
            networks,
            key=lambda network: (network.version, int(network.network_address)),
        )
        COUNTRY_NETS_TXT.write_text(
            render_lines(f"{format(key)} {networks[key]}" for key in keys)
        )
    print(format_status("build_products"))

    return networks


def lookup_country(ip: AddressType, path: Path) -> str | None:
    """Find an address country in a sorted network map.

    The map must be sorted by IP version and numeric network address,
    matching the output produced by :func:`tag_networks`.

    Parameters
    ----------
    ip : AddressType
        Address whose country code should be located.
    path : Path
        Path to the generated country network map.

    Returns
    -------
    str | None
        Matching country code, or ``None`` when the address is not
        represented in the map.
    """
    if not path.stat().st_size:
        return None

    target_key = ip.version, int(ip)
    candidate: tuple[NetworkType, str] | None = None

    with path.open("rb") as country_file:
        with mmap.mmap(country_file.fileno(), 0, access=mmap.ACCESS_READ) as data:
            first = 0
            last = len(data)

            while first < last:
                midpoint = (first + last) // 2
                data.seek(midpoint)
                if midpoint:
                    data.readline()
                line_start = data.tell()

                if line_start >= last:
                    last = midpoint
                    continue

                line = data.readline()
                next_line = data.tell()
                network_text, country_code = line.decode().split(maxsplit=1)
                network = ipa.ip_network(network_text)
                network_key = network.version, int(network.network_address)

                if network_key <= target_key:
                    candidate = network, country_code.strip()
                    first = next_line
                else:
                    last = midpoint

    if candidate and ip in candidate[0]:
        return candidate[1]
    return None


def load_country_networks() -> dict[NetworkType, str]:
    """Load the HAProxy country network map.

    Returns
    -------
    dict[NetworkType, str]
        The country network map keyed by IP network.
    """
    networks: dict[NetworkType, str] = {}
    with COUNTRY_NETS_TXT.open("r") as f:
        for line in f:
            try:
                network_text, country_code = line.strip().split(maxsplit=1)
                network = ipa.ip_network(network_text)
            except ValueError:
                continue
            networks[network] = country_code

    return networks


def load_ipsum() -> dict[AddressType, int]:
    """Load the ipsum.txt file into a dictionary.

    Returns
    -------
    dict[AddressType, int]
        The contents of ipsum.txt as a dictionary.
    """
    with IPSUM.open("r") as f:
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


def load_rendered_blocklist() -> tuple[list[AddressType], list[NetworkType]]:
    """Load the contents of the rendered blocklist.

    Separate it into sorted lists of IP addresses and networks.

    Returns
    -------
    tuple[list[AddressType], list[NetworkType]]
        The rendered blocklist split into IP addresses and networks.
    """
    with RENDERED_BLOCKLIST.open("r") as f:
        rendered = [token for line in f if (token := extract_ip(line.strip()))]
    return split_hybrid(rendered)
