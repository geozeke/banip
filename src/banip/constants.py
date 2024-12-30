"""Constants."""

from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path
from typing import TypeAlias

HOME = Path(__file__).parents[2]
DATA = HOME / "data"

APP_NAME = "banip"
ARG_PARSERS_BASE = HOME / "src" / "parsers"
ARG_PARSERS_CUSTOM = HOME / "src" / "plugins" / "parsers"
COUNTRY_NETS_TXT = DATA / "haproxy_geo_ip.txt"
COUNTRY_NETS_DICT = DATA / "haproxy_geo_ip_dict.bin"
COUNTRY_WHITELIST = DATA / "country_whitelist.txt"
CUSTOM_BLACKLIST = DATA / "custom_blacklist.txt"
CUSTOM_WHITELIST = DATA / "custom_whitelist.txt"
RENDERED_BLACKLIST = DATA / "ip_blacklist.txt"
RENDERED_WHITELIST = DATA / "ip_whitelist.txt"
CUSTOM_CODE = HOME / "src" / "plugins" / "code"
GEOLITE_4 = DATA / "geolite" / "GeoLite2-Country-Blocks-IPv4.csv"
GEOLITE_6 = DATA / "geolite" / "GeoLite2-Country-Blocks-IPv6.csv"
GEOLITE_LOC = DATA / "geolite" / "GeoLite2-Country-Locations-en.csv"
IPSUM = DATA / "ipsum.txt"
TARGETS = DATA / "targets.txt"
VERSION = "1.1.3"

# Padding for pretty printing
PAD = 30
# Type aliases for IP data types
AddressType: TypeAlias = IPv4Address | IPv6Address
NetworkType: TypeAlias = IPv4Network | IPv6Network
