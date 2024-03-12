#!/usr/bin/env python3

"""Analyze stats for a single country (two-letter code).

This is a *very* hacky utility that will allow me to pull stats for a
single country. It uses the build products from banip. It's not
production code, because it's heavily dependent on how my HAProxy logs
are formatted and how I pull the data from grafana, so it will be tough
to advertise it as available for general use. I'll still ship it with
banip, and maybe I'll incorporate it as a core capability at some point
in the future.
"""

import ipaddress as ipa
import re
import sys
from typing import Any

from banip.contants import BANNED_IPS
from banip.contants import HOME
from banip.contants import RENDERED_BLACKLIST
from banip.utilities import clear

target_country = sys.argv[1].upper()
regex = r"(?<=[\s=])(\w+)=([^=\s]+)(?=\s|$)"
LOGS = HOME / "data/logs.txt"
clear()

files = [BANNED_IPS, RENDERED_BLACKLIST, LOGS]
for file in files:
    if not file.exists():
        print(f"Cannot find {file}")
        sys.exit(1)

with open(LOGS, "r") as f:
    logs = f.readlines()
    # The first 5 lines contain header information.
    logs = logs[6:]

ipsum: dict[Any, int] = {}
with open(BANNED_IPS, "r") as f:
    for line in f:
        if (item := line.strip()) and item[0] != "#":
            parts = item.split()
            ipsum[ipa.ip_address(parts[0])] = int(parts[1])

blacklist: list[Any] = []
with open(RENDERED_BLACKLIST, "r") as f:
    for line in f:
        if (item := line.strip()) and item[0] != "#":
            # skip subnets
            if "/" not in item:
                blacklist.append(ipa.ip_address(item))

output: list[str] = []
target_ips: dict[Any, list[str]] = {}
for line in logs:
    groups = re.findall(regex, line)
    country = groups[-1][1]
    if country == target_country:
        ip = ipa.ip_address(groups[0][1])
        if ip not in blacklist:
            uri = groups[-2][1]
            if ip in target_ips:
                target_ips[ip].append(uri)
            else:
                target_ips[ip] = [uri]

for ip, uris in target_ips.items():
    output.append(f"IP: {format(ip)}\n")
    if ip in ipsum:
        output.append(f"Found in ipsum, with confidence of {ipsum[ip]}\n")
    if len(uris) == 1:
        output.append(f"Total of {len(uris)} request\n")
    else:
        output.append(f"Total of {len(uris)} requests\n")
    counter = 1
    for uri in uris:
        output.append(f"  {counter:>3}. {uri}\n")
        counter += 1
    output.append("\n")

msg = "IPs found in the logs, but not in the blacklist"
output.insert(0, f"Statistics for: {target_country}\n")
output.insert(1, f"{len(target_ips)} {msg}.\n\n")

print("".join(output).strip())
