"""Convert the Geolite Database to flat file."""

import csv
import ipaddress as ipa
from ipaddress import IPv4Network
from ipaddress import IPv6Network

from tqdm import tqdm  # type: ignore

from banip.contants import COUNTRY_CODES
from banip.contants import COUNTRY_ISO_CODE
from banip.contants import GEOLITE_4
from banip.contants import GEOLITE_6
from banip.contants import GEOLITE_LOC
from banip.contants import GEONAME_ID
from banip.contants import GEONET_ID


def make_haproxy() -> None:
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
            # There are some country codes in the csv file that reflect
            # continents (e.g. Europe). In that case, the
            # COUNTRY_ISO_CODE is blank, so we need to pull the
            # two-letter continent code from column 2 in the csv file.
            if not (cc := country[COUNTRY_ISO_CODE]):
                cc = country[2]
            countries_D[int(country[GEONAME_ID])] = cc

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
            try:
                country_code = countries_D[int(net[GEONET_ID])]
            except ValueError:
                continue
            ipv4_D[ipa.IPv4Network(net[0])] = country_code

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
            try:
                country_code = countries_D[int(net[1])]
            except ValueError:
                continue
            ipv6_D[ipa.IPv6Network(net[0])] = country_code

    print("\nGenerating files...", end="")
    keys_4 = list(ipv4_D.keys())
    keys_6 = list(ipv6_D.keys())
    keys_4.sort()
    keys_6.sort()
    key: IPv4Network | IPv6Network
    with open(COUNTRY_CODES, "w") as f:
        for key in keys_4:
            f.write(f"{format(key)} {ipv4_D[key]}\n")
        for key in keys_6:
            f.write(f"{format(key)} {ipv6_D[key]}\n")
    print("Done\n")
