import ipaddress as ipa
from datetime import datetime as dt

from banip.constants import CUSTOM_BLACKLIST
from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network
from banip.utilities import tag_networks

THRESHOLD = 2

# ----------------------------------------------------------------------

# Load custom blacklist and split it into lists of networks and
# addresses
print(f"{'Pruning custom blacklist':.<{PAD}}", end="", flush=True)
with open(CUSTOM_BLACKLIST, "r") as f:
    custom: list[AddressType | NetworkType] = [
        ip for line in f if (ip := extract_ip(line.strip()))
    ]
custom_nets: list[NetworkType] = sorted(
    [token for token in custom if isinstance(token, NetworkType)],
    key=lambda x: int(x.network_address),
)
custom_nets_size = len(custom_nets)
custom_ips: list[AddressType] = sorted(
    [token for token in custom if isinstance(token, AddressType)], key=lambda x: int(x)
)
# Remove any custom ips that are covered by existing custom subnets
custom_ips = [
    ip
    for ip in custom_ips
    if not ip_in_network(
        ip=ip, networks=custom_nets, first=0, last=custom_nets_size - 1
    )
]
print("done")

# ----------------------------------------------------------------------

# Geo-tag all global networks and save entries for target countries
geolite_D = tag_networks()
with open(TARGETS, "r") as f:
    countries = [
        token.upper() for line in f if (token := line.strip()) and token[0] != "#"
    ]
geolite = sorted(
    [key for key in geolite_D if geolite_D[key] in countries],
    key=lambda x: int(x.network_address),
)

# ----------------------------------------------------------------------

# Prune ipsum.txt to only keep ips from target countries, ips that are
# not already covered by a custom subnet, and ips that meet the minimum
# threshold for number of hits.
print(f"{'Pruning ipsum.txt':.<{PAD}}", end="", flush=True)
with open(IPSUM, "r") as f:
    ipsum: list[AddressType] = []
    geolite_size = len(geolite)
    for line in f:
        parts = line.strip().split()
        try:
            ip = ipa.ip_address(parts[0])
            hits = int(parts[1])
        except (ValueError, NameError):
            continue
        if (
            ip_in_network(ip=ip, networks=geolite, first=0, last=geolite_size - 1)
            and not ip_in_network(
                ip=ip,
                networks=custom_nets,
                first=0,
                last=custom_nets_size - 1,
            )
            and (hits >= THRESHOLD)
        ):
            ipsum.append(ip)
    ipsum = sorted(ipsum, key=lambda x: int(x))
print("done")

# ----------------------------------------------------------------------

# Remove any custom ips that are already covered by ipsum.txt.
print(f"{'De-duplicating custom ips':.<{PAD}}", end="", flush=True)
custom_ips = [ip for ip in custom_ips if ip not in ipsum]
print("done")

# ----------------------------------------------------------------------

# Re-package and save custom nets and ips
print(f"{'Re-packaging custom ips':.<{PAD}}", end="", flush=True)
with open(CUSTOM_BLACKLIST, "w") as f:
    for ip in custom_ips:
        f.write(f"{ip}\n")
    for net in custom_nets:
        f.write(f"{net}\n")
print("done")

# ----------------------------------------------------------------------

# Render and save the complete ip_blacklist.txt
print(f"{'Rendering blacklist':.<{PAD}}", end="", flush=True)
with open(RENDERED_BLACKLIST, "w") as f:
    for ip in ipsum:
        f.write(f"{ip}\n")
    now = dt.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write("\n# ------------custom entries -------------\n")
    f.write(f"# Added on: {now}\n")
    f.write("# ----------------------------------------\n\n")
    for ip in custom_ips:
        f.write(f"{ip}\n")
    for net in custom_nets:
        f.write(f"{net}\n")
print("done")
