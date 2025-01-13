"""Constants."""

from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path
from typing import TypeAlias

HOME = Path.home()
BASE = Path(__file__).parents[0]
DATA = HOME / ".banip"

APP_NAME = "banip"
ARG_PARSERS_BASE = BASE / "parsers"
CUSTOM_CODE = DATA / "plugins" / "code"
CUSTOM_PARSERS = DATA / "plugins" / "parsers"
COUNTRY_NETS_TXT = DATA / "haproxy_geo_ip.txt"
COUNTRY_NETS_DICT = DATA / "haproxy_geo_ip_dict.bin"
COUNTRY_WHITELIST = DATA / "country_whitelist.txt"
CUSTOM_BLACKLIST = DATA / "custom_blacklist.txt"
CUSTOM_WHITELIST = DATA / "custom_whitelist.txt"
RENDERED_BLACKLIST = DATA / "ip_blacklist.txt"
RENDERED_WHITELIST = DATA / "ip_whitelist.txt"
GEOLITE_4 = DATA / "geolite" / "GeoLite2-Country-Blocks-IPv4.csv"
GEOLITE_6 = DATA / "geolite" / "GeoLite2-Country-Blocks-IPv6.csv"
GEOLITE_LOC = DATA / "geolite" / "GeoLite2-Country-Locations-en.csv"
IPSUM = DATA / "ipsum.txt"
TARGETS = DATA / "targets.txt"

# Padding for pretty printing
PAD = 30
# Type aliases for IP data types
AddressType: TypeAlias = IPv4Address | IPv6Address
NetworkType: TypeAlias = IPv4Network | IPv6Network
