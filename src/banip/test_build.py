import ipaddress as ipa

from banip.constants import CUSTOM_BLACKLIST
from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network
from banip.utilities import tag_networks

THRESHOLD = 2

# Load custom blacklist and split it into lists of networks and
# addresses
with open(CUSTOM_BLACKLIST, "r") as f:
    custom: set[AddressType | NetworkType] = {
        ip for line in f if (ip := extract_ip(line.strip()))
    }

# Geo-tag networks and pull entries for target countries
geolite_D = tag_networks()
with open(TARGETS, "r") as f:
    countries = [
        token.upper() for line in f if (token := line.strip()) and token[0] != "#"
    ]
geolite = [key for key in geolite_D if geolite_D[key] in countries]
geolite = sorted(geolite, key=lambda x: int(x.network_address))

# Prune ipsum.txt to remove ips from non-target countries, as well as
# those which don't meet the minimum threshold for number of hits.
print(f"{'Pruning ipsum.txt':.<{PAD}}", end="", flush=True)
with open(IPSUM, "r") as f:
    ipsum: set[AddressType] = set()
    size = len(geolite)
    for line in f:
        parts = line.strip().split()
        try:
            ip = ipa.ip_address(parts[0])
            hits = int(parts[1])
        except (ValueError, NameError):
            continue
        if (
            ip_in_network(ip=ip, networks=geolite, first=0, last=size - 1)
            and hits >= THRESHOLD
        ):
            ipsum.add(ip)
print("done")

pretty = sorted(list(ipsum), key=lambda x: int(x))
with open("junk.txt", "w") as f:
    for ip in pretty:
        f.write(f"{ip}\n")
