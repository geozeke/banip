"""Convert the Geolite Database to flat file."""

import csv
import ipaddress as ipa
from ipaddress import IPv4Network
from ipaddress import IPv6Network

from tqdm import tqdm  # type: ignore

from banip.contants import COUNTRY_CODES
from banip.contants import GEOLITE_4
from banip.contants import GEOLITE_6
from banip.contants import GEOLITE_LOC


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
