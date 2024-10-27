#! /usr/bin/env python3

"""Build a custom list of banned ips."""

import ipaddress as ipa
import shutil
import sys
from argparse import Namespace
from datetime import datetime as dt
from pathlib import Path

from banip.constants import COUNTRY_WHITELIST
from banip.constants import CUSTOM_BLACKLIST
from banip.constants import CUSTOM_WHITELIST
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM
from banip.constants import PAD
from banip.constants import RENDERED_BLACKLIST
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
from banip.utilities import tag_networks


def task_runner(args: Namespace) -> None:
    """Generate a custom list of banned IP addresses.

    Parameters
    ----------
    args : Namespace
        Command line arguments.
    """
    # ------------------------------------------------------------------

    # Start by stubbing-out custom files if they're not already in
    # place. In the case of the output file, check for two things: (1)
    # Was a file specified? If not, then save results to the default
    # (RENDERED_BLACKLIST). (2) If the file was specified, was it the
    # same name as the default? If so, there's no need to make a local
    # copy of it after computations are complete.
    print()
    make_local_copy = False
    if not CUSTOM_BLACKLIST.exists():
        f = open(CUSTOM_BLACKLIST, "w")
        f.close()
    if not CUSTOM_WHITELIST.exists():
        f = open(CUSTOM_WHITELIST, "w")
        f.close()
    try:
        if Path(args.outfile.name) != RENDERED_BLACKLIST:
            make_local_copy = True
    except AttributeError:
        args.outfile = open(RENDERED_BLACKLIST, "w")

    # ------------------------------------------------------------------

    # Now make sure everything is in place
    files = [
        CUSTOM_BLACKLIST,
        CUSTOM_WHITELIST,
        GEOLITE_4,
        GEOLITE_6,
        GEOLITE_LOC,
        IPSUM,
        RENDERED_BLACKLIST,
        TARGETS,
    ]
    for file in files:
        if not file.exists():
            print(f"Missing file: {file}")
            print("Visit https://github.com/geozeke/banip for more info.")
            sys.exit(1)

    # ------------------------------------------------------------------

    # Load custom blacklist and split it into separate lists of networks
    # and addresses.
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
        [token for token in custom if isinstance(token, AddressType)],
        key=lambda x: int(x),
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

    # ------------------------------------------------------------------

    # Geotag all global networks and save entries for target countries
    geolite_D = tag_networks()
    with open(TARGETS, "r") as f:
        countries = [
            token.upper() for line in f if (token := line.strip()) and token[0] != "#"
        ]
    geolite = sorted(
        [net for net in geolite_D if geolite_D[net] in countries],
        key=lambda x: int(x.network_address),
    )
    geolite_size = len(geolite)

    # Save the cleaned-up country codes for later use in HAProxy
    print(f"{'Saving country whitelist':.<{PAD}}", end="", flush=True)
    countries.sort()
    with open(COUNTRY_WHITELIST, "w") as f:
        f.write(f"{'\n'.join(countries)}\n")
    print("done")

    # ------------------------------------------------------------------

    # Prune ipsum.txt to only keep ips (1) from target countries, (2)
    # ips that are not already covered by a custom subnet, (3) ips that
    # meet the minimum threshold for number of hits, and (4) ips that
    # are not in the custom whitelist.
    print(f"{'Pruning ipsum.txt':.<{PAD}}", end="", flush=True)
    whitelist: list[AddressType] = []
    with open(CUSTOM_WHITELIST, "r") as f:
        for line in f:
            try:
                ip = ipa.ip_address(line.strip())
                whitelist.append(ip)
            except ValueError:
                continue

    ipsum_D: dict[AddressType, int] = load_ipsum()
    ipsum: list[AddressType] = [
        ip
        for ip in ipsum_D
        if (
            ip_in_network(ip=ip, networks=geolite, first=0, last=geolite_size - 1)
            and not ip_in_network(
                ip=ip, networks=custom_nets, first=0, last=custom_nets_size - 1
            )
            and ip not in whitelist
            and ipsum_D[ip] >= args.threshold
        )
    ]
    ipsum = sorted(ipsum, key=lambda x: int(x))
    ipsum_size = len(ipsum)
    print("done")

    # ------------------------------------------------------------------

    # Prune any custom ips that are covered by ipsum.txt.
    print(f"{'De-duplicating custom ips':.<{PAD}}", end="", flush=True)
    custom_ips = [ip for ip in custom_ips if ip not in ipsum]
    custom_ips_size = len(custom_ips)
    print("done")

    # ------------------------------------------------------------------

    # Re-package and save cleaned-up custom ips and networks
    print(f"{'Re-packaging custom ips':.<{PAD}}", end="", flush=True)
    with open(CUSTOM_BLACKLIST, "w") as f:
        for ip in custom_ips:
            f.write(f"{ip}\n")
        for net in custom_nets:
            f.write(f"{net}\n")
    print("done")

    # ------------------------------------------------------------------

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

    args.outfile.close()
    if make_local_copy:
        shutil.copy(Path(args.outfile.name), RENDERED_BLACKLIST)
    print(f"{'Blacklist entries saved':.<{PAD}}", end="", flush=True)
    total_size = ipsum_size + custom_nets_size + custom_ips_size
    print(f"{(total_size):,d}")
    print(f"{'Whitelisted countries':.<{PAD}}", end="", flush=True)
    print(",".join(countries))

    return


if __name__ == "__main__":
    pass
