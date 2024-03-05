#! /usr/bin/env python3

"""Create a custom list of banned ips."""

import ipaddress as ipa
from pathlib import Path

from tqdm import tqdm  # type: ignore

HOME = Path(__file__).parents[2]
COUNTRY_CODES = HOME / "data/haproxy_geo_ip.txt"
BANNED_IPS = HOME / "data/ipsum.txt"
CUSTOM_BANS = HOME / "data/custom_bans.txt"
COUNTRIES = "NO US".split()
COUNTRIES.sort()
OUTFILE = "./data/junk.txt"
MIN_HITS = 3
PAD = 6

# First count number of lines in country codes file, then process each
# one by adding it to a dictionary with IP network objects as keys, and
# two-letter country codes as values. Skip lines starting with hastags,
# and those that are not in the desired set of countries to examine.

networks_L: list[ipa.IPv4Network | ipa.IPv6Network] = []
print(f"\nPulling networks for country codes: {COUNTRIES}")
with open(COUNTRY_CODES, "r") as f:
    lines = len(f.readlines())
    f.seek(0)
    for line in tqdm(
        f,
        desc="Lines",
        total=lines,
        colour="#bf80f2",
        unit="lines",
    ):
        cleanline = line.strip()
        if cleanline[0] == "#" or cleanline == "":
            continue
        else:
            parts = cleanline.split()
            if parts[1] in COUNTRIES:
                networks_L.append(ipa.ip_network(parts[0], strict=False))
print(f"Lines analysed: {lines:,d}; Networks pulled: {len(networks_L):,d}")

# Now process the file of blacklisted IPs, filtering out those that have
# less than the desired number of blacklist occurrences (hits)

print()
banned_L: list[ipa.IPv4Address | ipa.IPv6Address] = []
print(f"Pulling blacklisted IPs with >= {MIN_HITS} hits.")
with open(BANNED_IPS, "r") as f:
    lines = len(f.readlines())
    f.seek(0)
    for line in tqdm(
        f,
        desc="Lines",
        total=lines,
        colour="#bf80f2",
        unit="lines",
    ):
        cleanline = line.strip()
        if cleanline[0] == "#" or cleanline == "":
            continue
        else:
            parts = cleanline.split()
            count = int(parts[1])
            if count >= MIN_HITS:
                banned_L.append(ipa.ip_address(parts[0]))
print(f"Lines analysed: {lines:,d}; IPs pulled: {len(banned_L):,d}")

# This part takes the longest. Store those blacklisted IPs that are
# hosted on the networks of target countries.

print()
TEMP_L: list[ipa.IPv4Address | ipa.IPv6Address] = []
print(f"Building banned IP list for country codes: {COUNTRIES}")
for ip in tqdm(
    banned_L,
    desc="IPs",
    total=len(banned_L),
    colour="#bf80f2",
    unit="IPs",
):
    for network in networks_L:
        if ip in network:
            TEMP_L.append(ip)
            break
print(f"IPs analysed: {len(banned_L):,d}; IPs pulled: {len(TEMP_L):,d}")

# Open the custom bans list and prune any IPs that were already
# discovered while building the list of banned IPs

custom_bans: list[ipa.IPv4Address | ipa.IPv6Address] = []
with open(CUSTOM_BANS, "r") as f:
    for line in f:
        cleanline = line.strip()
        if cleanline[0] != "#" and cleanline != "":
            custom_bans.append(ipa.ip_address(cleanline))
new_custom = [ip for ip in custom_bans if ip not in TEMP_L]

# Merge the custom bans

with open(CUSTOM_BANS, "w") as f:
    for ip in new_custom:
        f.write(f"{format(ip)}\n")

# Write banned IPs to the file

TEMP_L += new_custom
TEMP_L.sort()
with open(OUTFILE, "w") as f:
    for ip in TEMP_L:
        f.write(f"{format(ip)}\n")

print(f"\n         Band IPs found: {len(TEMP_L)-len(custom_bans):>{PAD},d}")
print(f"   Custom bans provided: {len(custom_bans):>{PAD},d}")
print(f"     Duplicates removed: {len(custom_bans)-len(new_custom):>{PAD},d}")
print(f" Total banned IPs saved: {len(TEMP_L):>{PAD},d}")
