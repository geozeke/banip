"""Constants."""

from ipaddress import IPv4Address
from ipaddress import IPv4Network
from ipaddress import IPv6Address
from ipaddress import IPv6Network
from pathlib import Path

HOME = Path(__file__).parents[2]

APP_NAME = "banip"
ARG_PARSERS_BASE = HOME / "src" / "parsers"
ARG_PARSERS_CUSTOM = HOME / "src" / "plugins" / "parsers"
BANNED_IPS = HOME / "data" / "ipsum.txt"
COUNTRY_NETS = HOME / "data" / "haproxy_geo_ip.txt"
CUSTOM_BLACKLIST = HOME / "data" / "custom_blacklist.txt"
CUSTOM_CODE = HOME / "src" / "plugins" / "code"
CUSTOM_WHITELIST = HOME / "data" / "custom_whitelist.txt"
GEOLITE_4 = HOME / "data" / "geolite" / "GeoLite2-Country-Blocks-IPv4.csv"
GEOLITE_6 = HOME / "data" / "geolite" / "GeoLite2-Country-Blocks-IPv6.csv"
GEOLITE_LOC = HOME / "data" / "geolite" / "GeoLite2-Country-Locations-en.csv"
IPS = [IPv4Address, IPv6Address]
NETS = [IPv4Network, IPv6Network]
RENDERED_BLACKLIST = HOME / "data" / "ip_blacklist.txt"
TARGETS = HOME / "data" / "targets.txt"
VERSION = "1.0.2"

# Padding for pretty printing.
PAD = 6
