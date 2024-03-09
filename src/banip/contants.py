"""Constants."""

from pathlib import Path

HOME = Path(__file__).parents[2]

BANNED_IPS = HOME / "data/ipsum.txt"
COUNTRY_CODES = HOME / "data/haproxy_geo_ip.txt"
CUSTOM_BANS = HOME / "data/custom_bans.txt"
GEOLITE_4 = HOME / "data/geolite/GeoLite2-Country-Blocks-IPv4.csv"
GEOLITE_6 = HOME / "data/geolite/GeoLite2-Country-Blocks-IPv6.csv"
GEOLITE_LOC = HOME / "data/geolite/GeoLite2-Country-Locations-en.csv"
TARGETS = HOME / "data/targets.txt"

# Padding for pretty printing.
PAD = 6
