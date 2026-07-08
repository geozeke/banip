"""Manage crawler and bot provider IP ranges."""

import ipaddress as ipa
import json
import socket
from argparse import Namespace
from collections.abc import Iterable
from datetime import UTC
from datetime import datetime as dt
from typing import Any
from typing import cast

import requests
from rich import box
from rich.console import Console
from rich.table import Table

from banip.constants import BOTDATA
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import build_network_lookup
from banip.utilities import ip_in_network

PROVIDER_URLS = {
    "google": (
        "https://developers.google.com/static/crawling/ipranges/common-crawlers.json",
        "https://developers.google.com/static/crawling/ipranges/special-crawlers.json",
        "https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json",
        "https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json",
    ),
    "bing": ("https://www.bing.com/toolbox/bingbot.json",),
    "openai": (
        "https://openai.com/searchbot.json",
        "https://openai.com/adsbot.json",
        "https://openai.com/gptbot.json",
        "https://openai.com/chatgpt-user.json",
    ),
    "meta": (),
}
PROVIDERS = tuple(PROVIDER_URLS)
META_WHOIS_HOST = "whois.radb.net"
META_WHOIS_QUERY = "-i origin AS32934"
META_WHOIS_SOURCE = f"whois://{META_WHOIS_HOST}/{META_WHOIS_QUERY}"


def sort_networks(networks: Iterable[NetworkType]) -> list[NetworkType]:
    """Sort networks by IP version and network address.

    Parameters
    ----------
    networks : Iterable[NetworkType]
        Networks to sort.

    Returns
    -------
    list[NetworkType]
        Sorted network objects.
    """
    return sorted(networks, key=lambda net: (net.version, int(net.network_address)))


def normalize_ranges(payloads: Iterable[dict[str, Any]]) -> list[str]:
    """Normalize provider JSON payloads into deduplicated CIDR strings.

    Parameters
    ----------
    payloads : Iterable[dict[str, Any]]
        JSON payloads with ``prefixes`` entries.

    Returns
    -------
    list[str]
        Deduplicated CIDR strings sorted deterministically.
    """
    networks: set[NetworkType] = set()
    for payload in payloads:
        prefixes = payload.get("prefixes", [])
        if not isinstance(prefixes, list):
            continue
        for item in prefixes:
            if not isinstance(item, dict):
                continue
            prefix = item.get("ipv4Prefix") or item.get("ipv6Prefix")
            if isinstance(prefix, str):
                networks.add(ipa.ip_network(prefix))

    return [str(network) for network in sort_networks(networks)]


def parse_irr_ranges(text: str) -> list[str]:
    """Normalize IRR route data into deduplicated CIDR strings.

    Parameters
    ----------
    text : str
        Raw RPSL-style IRR response text.

    Returns
    -------
    list[str]
        Deduplicated CIDR strings sorted deterministically.
    """
    networks: set[NetworkType] = set()
    for line in text.splitlines():
        if not line.startswith(("route:", "route6:")):
            continue
        _, _, value = line.partition(":")
        try:
            networks.add(ipa.ip_network(value.strip()))
        except ValueError:
            continue

    return [str(network) for network in sort_networks(networks)]


def collect_upstream_timestamp(payloads: Iterable[dict[str, Any]]) -> str | None:
    """Collect the newest upstream timestamp exposed by a provider.

    Parameters
    ----------
    payloads : Iterable[dict[str, Any]]
        JSON payloads returned by provider feeds.

    Returns
    -------
    str | None
        The newest upstream timestamp if one exists; otherwise None.
    """
    timestamps: list[str] = []
    for payload in payloads:
        for key in ("creationTime", "syncToken"):
            timestamp = payload.get(key)
            if isinstance(timestamp, str) and timestamp:
                timestamps.append(timestamp)
    if not timestamps:
        return None
    return sorted(timestamps)[-1]


def query_whois(host: str, query: str, timeout: int = 30) -> str:
    """Query a WHOIS server and return raw response text.

    Parameters
    ----------
    host : str
        WHOIS server hostname.
    query : str
        Query string to send.
    timeout : int, optional
        Socket timeout in seconds. Defaults to 30.

    Returns
    -------
    str
        Decoded WHOIS response text.
    """
    chunks: list[bytes] = []
    with socket.create_connection((host, 43), timeout=timeout) as connection:
        connection.sendall(f"{query}\r\n".encode())
        while chunk := connection.recv(65536):
            chunks.append(chunk)
    return b"".join(chunks).decode(errors="replace")


def fetch_provider(provider: str) -> dict[str, object]:
    """Fetch and normalize one provider's managed ranges.

    Parameters
    ----------
    provider : str
        Provider key to refresh.

    Returns
    -------
    dict[str, object]
        Normalized provider data ready for storage.
    """
    if provider == "meta":
        return {
            "provider": provider,
            "source": [META_WHOIS_SOURCE],
            "refreshed_at": dt.now(UTC).isoformat(timespec="seconds"),
            "ranges": parse_irr_ranges(query_whois(META_WHOIS_HOST, META_WHOIS_QUERY)),
        }

    payloads = []
    for url in PROVIDER_URLS[provider]:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payloads.append(response.json())

    entry: dict[str, object] = {
        "provider": provider,
        "source": list(PROVIDER_URLS[provider]),
        "refreshed_at": dt.now(UTC).isoformat(timespec="seconds"),
        "ranges": normalize_ranges(payloads),
    }
    if upstream_timestamp := collect_upstream_timestamp(payloads):
        entry["upstream_updated_at"] = upstream_timestamp
    return entry


def load_botdata() -> dict[str, Any]:
    """Load stored bot data.

    Returns
    -------
    dict[str, Any]
        Bot data grouped by provider.
    """
    if not BOTDATA.exists():
        return {"providers": {}}
    return cast(dict[str, Any], json.loads(BOTDATA.read_text()))


def write_botdata(data: dict[str, Any]) -> None:
    """Write bot data with deterministic provider and range ordering.

    Parameters
    ----------
    data : dict[str, Any]
        Bot data grouped by provider.
    """
    providers = data.get("providers", {})
    ordered: dict[str, object] = {}
    if isinstance(providers, dict):
        for provider in sorted(providers):
            entry = providers[provider]
            if not isinstance(entry, dict):
                continue
            ranges = entry.get("ranges", [])
            if isinstance(ranges, list):
                networks = [
                    ipa.ip_network(item) for item in ranges if isinstance(item, str)
                ]
                entry["ranges"] = [str(net) for net in sort_networks(networks)]
            ordered[provider] = entry
    BOTDATA.parent.mkdir(parents=True, exist_ok=True)
    BOTDATA.write_text(json.dumps({"providers": ordered}, indent=2) + "\n")


def load_managed_bot_networks(
    providers: Iterable[str] | None = None,
) -> dict[str, list[NetworkType]]:
    """Load stored managed bot ranges as network objects.

    Parameters
    ----------
    providers : Iterable[str] | None, optional
        Provider keys to include. Defaults to all stored providers.

    Returns
    -------
    dict[str, list[NetworkType]]
        Managed bot networks grouped by provider.
    """
    data = load_botdata()
    stored_providers = data.get("providers", {})
    if not isinstance(stored_providers, dict):
        return {}

    requested = set(providers) if providers else set(stored_providers)
    networks: dict[str, list[NetworkType]] = {}
    for provider in sorted(requested):
        entry = stored_providers.get(provider, {})
        if not isinstance(entry, dict):
            continue
        ranges = entry.get("ranges", [])
        if not isinstance(ranges, list):
            continue
        networks[provider] = sort_networks(
            ipa.ip_network(item) for item in ranges if isinstance(item, str)
        )
    return networks


def refresh(provider: str) -> None:
    """Refresh one provider or all providers.

    Parameters
    ----------
    provider : str
        Provider key, or ``all`` for every known provider.
    """
    data = load_botdata()
    stored_providers = data.setdefault("providers", {})
    if not isinstance(stored_providers, dict):
        stored_providers = {}
        data["providers"] = stored_providers

    selected = PROVIDERS if provider == "all" else (provider,)
    for item in selected:
        entry = fetch_provider(item)
        stored_providers[item] = entry
        ranges = entry.get("ranges", [])
        range_count = len(ranges) if isinstance(ranges, list) else 0
        print(f"Refreshed {item}: {range_count:,d} ranges")
    write_botdata(data)
    print(f"Saved {BOTDATA}")


def list_providers() -> None:
    """List stored bot provider range counts."""
    data = load_botdata()
    providers = data.get("providers", {})
    table = Table(title="Managed Bot Ranges", box=box.SQUARE)
    table.add_column("Provider")
    table.add_column("Ranges", justify="right")
    table.add_column("Last Refreshed")

    if isinstance(providers, dict):
        for provider in sorted(providers):
            entry = providers[provider]
            if not isinstance(entry, dict):
                continue
            ranges = entry.get("ranges", [])
            range_count = len(ranges) if isinstance(ranges, list) else 0
            refreshed_at = entry.get("refreshed_at", "--")
            table.add_row(provider, f"{range_count:,d}", str(refreshed_at))

    console = Console()
    console.print(table)


def check_ip(ip: AddressType) -> None:
    """Check whether an IP address appears in managed bot ranges.

    Parameters
    ----------
    ip : AddressType
        IP address to check.
    """
    matches = []
    for provider, networks in load_managed_bot_networks().items():
        lookup = build_network_lookup(networks)
        if network := ip_in_network(ip=ip, lookup=lookup):
            matches.append((provider, network))

    if not matches:
        print(f"{ip} not found in managed bot ranges.")
        return

    for provider, network in matches:
        print(f"{ip} found in {provider}: {network}")


def task_runner(args: Namespace) -> None:
    """Run the selected bots subcommand.

    Parameters
    ----------
    args : Namespace
        Command-line arguments.
    """
    if args.action == "refresh":
        refresh(args.provider)
    elif args.action == "list":
        list_providers()
    elif args.action == "check":
        check_ip(args.ip)


if __name__ == "__main__":
    pass
