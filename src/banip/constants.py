"""Constants."""

from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path
from typing import TypeAlias

HOME = Path(__file__).parents[2]

APP_NAME = "banip"
ARG_PARSERS_BASE = HOME / "src" / "parsers"
ARG_PARSERS_CUSTOM = HOME / "src" / "plugins" / "parsers"
COUNTRY_NETS_TXT = HOME / "data" / "haproxy_geo_ip.txt"
COUNTRY_NETS_DICT = HOME / "data" / "haproxy_geo_ip_dict.bin"
COUNTRY_WHITELIST = HOME / "data" / "country_whitelist.txt"
CUSTOM_BLACKLIST = HOME / "data" / "custom_blacklist.txt"
CUSTOM_CODE = HOME / "src" / "plugins" / "code"
CUSTOM_WHITELIST = HOME / "data" / "custom_whitelist.txt"
GEOLITE_4 = HOME / "data" / "geolite" / "GeoLite2-Country-Blocks-IPv4.csv"
GEOLITE_6 = HOME / "data" / "geolite" / "GeoLite2-Country-Blocks-IPv6.csv"
GEOLITE_LOC = HOME / "data" / "geolite" / "GeoLite2-Country-Locations-en.csv"
IPSUM = HOME / "data" / "ipsum.txt"
RENDERED_BLACKLIST = HOME / "data" / "ip_blacklist.txt"
TARGETS = HOME / "data" / "targets.txt"
VERSION = "1.1.2"

# Padding for pretty printing
PAD = 30
# Type aliases for IP data types
AddressType: TypeAlias = IPv4Address | IPv6Address
NetworkType: TypeAlias = IPv4Network | IPv6Network
