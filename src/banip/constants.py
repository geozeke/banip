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
BOTDATA = DATA / "botdata.json"
CONFIG = DATA / "banip.yaml"
COUNTRY_NETS_TXT = DATA / "haproxy_geo_ip.txt"
COUNTRY_ALLOWLIST = DATA / "country_allowlist.txt"
LEGACY_CUSTOM_ALLOWLIST = DATA / "custom_whitelist.txt"
LEGACY_CUSTOM_DENYLIST = DATA / "custom_blacklist.txt"
RENDERED_ALLOWLIST = DATA / "ip_allowlist.txt"
RENDERED_BLOCKLIST = DATA / "ip_blocklist.txt"
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
AddressTypes = (IPv4Address, IPv6Address)
NetworkTypes = (IPv4Network, IPv6Network)
