"""Tests for shared utility functions."""

import ipaddress as ipa
from types import SimpleNamespace

from requests.exceptions import RequestException

from banip import utilities


def test_print_docstring_removes_common_indent(capsys) -> None:
    """Formatted docstrings are printed without leading indentation."""
    utilities.print_docstring(
        """
        First line
            Second line
        """
    )

    assert capsys.readouterr().out == "First line\n    Second line\n\n"


def test_format_status_uses_checkmark_and_aligned_leader() -> None:
    """Status lines use a check mark and align with registered labels."""
    assert (
        utilities.format_status("custom_prune")
        == "Pruning custom blacklist..........✅"
    )


def test_format_status_uses_minimum_three_dot_leader() -> None:
    """Long status labels still receive at least three leader dots."""
    assert utilities.format_status("repack") == "Repackaging custom IP addresses...✅"


def test_format_status_aligns_all_registered_statuses() -> None:
    """Registered status values start in the same output column."""
    status_index = utilities.format_status("repack").index("✅")

    for key in utilities.STATUS_MESSAGES.labels:
        kwargs: dict[str, object] = {"compact": 10} if key == "ipsum_compact" else {}
        assert utilities.format_status(key, **kwargs).index("✅") == status_index  # type: ignore


def test_format_status_preserves_custom_status() -> None:
    """Custom status values are formatted with the same leader rule."""
    status_line = utilities.format_status("ipsum_compact", "47.26%", compact=10)

    assert status_line == "Compacting ipsum (10).............47.26%"
    assert status_line.index("47.26%") == utilities.format_status("repack").index("✅")


def test_status_label_raises_for_unknown_key() -> None:
    """Unknown status message keys fail clearly."""
    try:
        utilities.status_label("missing")
    except KeyError as exc:
        assert exc.args == ("missing",)
    else:
        raise AssertionError("Expected KeyError")


def test_split_hybrid_sorts_addresses_and_networks() -> None:
    """Mixed IP data is split and sorted deterministically."""
    mixed = [
        ipa.ip_network("10.0.1.0/24"),
        ipa.ip_address("10.0.0.2"),
        ipa.ip_network("10.0.0.0/24"),
        ipa.ip_address("10.0.0.1"),
    ]

    ips, nets = utilities.split_hybrid(mixed)

    assert ips == [ipa.ip_address("10.0.0.1"), ipa.ip_address("10.0.0.2")]
    assert nets == [ipa.ip_network("10.0.0.0/24"), ipa.ip_network("10.0.1.0/24")]


def test_extract_ip_parses_addresses_networks_and_invalid_values() -> None:
    """IP extraction accepts valid addresses and networks only."""
    assert utilities.extract_ip("192.0.2.1") == ipa.ip_address("192.0.2.1")
    assert utilities.extract_ip("192.0.2.0/24") == ipa.ip_network("192.0.2.0/24")
    assert utilities.extract_ip("not-an-ip") is None


def test_compact_can_disable_or_create_subnets() -> None:
    """Compaction returns either sorted IPs or eligible /24 networks."""
    ips = [
        ipa.ip_address("192.0.2.3"),
        ipa.ip_address("192.0.2.1"),
        ipa.ip_address("2001:db8::1"),
    ]

    loose_ips, loose_nets = utilities.compact(ips, whitelist=[], min_num=0)
    compact_ips, compact_nets = utilities.compact(ips, whitelist=[], min_num=2)

    assert loose_ips == [
        ipa.ip_address("192.0.2.1"),
        ipa.ip_address("192.0.2.3"),
        ipa.ip_address("2001:db8::1"),
    ]
    assert loose_nets == []
    assert compact_ips == [ipa.ip_address("2001:db8::1")]
    assert compact_nets == [ipa.ip_network("192.0.2.0/24")]


def test_compact_respects_whitelisted_networks() -> None:
    """Whitelisted ranges prevent subnet compaction."""
    ips = [ipa.ip_address("192.0.2.1"), ipa.ip_address("192.0.2.3")]
    whitelist = [ipa.ip_network("192.0.2.0/28")]

    compact_ips, compact_nets = utilities.compact(ips, whitelist=whitelist, min_num=2)

    assert compact_ips == ips
    assert compact_nets == []


def test_build_network_lookup_splits_and_sorts_network_bounds() -> None:
    """Lookup data is sorted and split by IP address family."""
    networks = [
        ipa.ip_network("2001:db8:1::/48"),
        ipa.ip_network("198.51.100.0/24"),
        ipa.ip_network("192.0.2.0/24"),
        ipa.ip_network("2001:db8::/48"),
    ]

    lookup = utilities.build_network_lookup(networks)

    assert [bounds.network for bounds in lookup.ipv4] == [
        ipa.ip_network("192.0.2.0/24"),
        ipa.ip_network("198.51.100.0/24"),
    ]
    assert [bounds.network for bounds in lookup.ipv6] == [
        ipa.ip_network("2001:db8::/48"),
        ipa.ip_network("2001:db8:1::/48"),
    ]


def test_ip_in_network_finds_ipv4_boundaries_and_misses() -> None:
    """Lookup returns IPv4 networks for range boundaries only."""
    lookup = utilities.build_network_lookup(
        [
            ipa.ip_network("192.0.2.0/24"),
            ipa.ip_network("198.51.100.0/24"),
        ]
    )

    assert utilities.ip_in_network(ipa.ip_address("198.51.100.0"), lookup) == (
        ipa.ip_network("198.51.100.0/24")
    )
    assert utilities.ip_in_network(ipa.ip_address("198.51.100.255"), lookup) == (
        ipa.ip_network("198.51.100.0/24")
    )
    assert utilities.ip_in_network(ipa.ip_address("198.51.99.255"), lookup) is None
    assert utilities.ip_in_network(ipa.ip_address("198.51.101.0"), lookup) is None


def test_ip_in_network_finds_ipv6_boundaries_and_misses() -> None:
    """Lookup returns IPv6 networks for range boundaries only."""
    lookup = utilities.build_network_lookup([ipa.ip_network("2001:db8::/126")])

    assert utilities.ip_in_network(ipa.ip_address("2001:db8::"), lookup) == (
        ipa.ip_network("2001:db8::/126")
    )
    assert utilities.ip_in_network(ipa.ip_address("2001:db8::3"), lookup) == (
        ipa.ip_network("2001:db8::/126")
    )
    assert utilities.ip_in_network(ipa.ip_address("2001:db8::4"), lookup) is None


def test_ip_in_network_uses_matching_address_family() -> None:
    """Mixed lookup data only searches the target address family."""
    lookup = utilities.build_network_lookup(
        [
            ipa.ip_network("::/0"),
            ipa.ip_network("192.0.2.0/24"),
        ]
    )

    assert utilities.ip_in_network(ipa.ip_address("192.0.2.1"), lookup) == (
        ipa.ip_network("192.0.2.0/24")
    )
    assert utilities.ip_in_network(ipa.ip_address("2001:db8::1"), lookup) == (
        ipa.ip_network("::/0")
    )


def test_ip_in_network_handles_empty_lookup() -> None:
    """Empty lookup data never returns a containing network."""
    lookup = utilities.build_network_lookup([])

    assert utilities.ip_in_network(ipa.ip_address("192.0.2.1"), lookup) is None


def test_load_ipsum_skips_malformed_lines(tmp_path, monkeypatch) -> None:
    """The ipsum loader ignores invalid and incomplete records."""
    ipsum = tmp_path / "ipsum.txt"
    ipsum.write_text(
        "\n192.0.2.1 5\ninvalid 7\n198.51.100.1\n203.0.113.1 not-a-number\n"
    )
    monkeypatch.setattr(utilities, "IPSUM", ipsum)

    assert utilities.load_ipsum() == {ipa.ip_address("192.0.2.1"): 5}


def test_load_rendered_blacklist_splits_file(tmp_path, monkeypatch) -> None:
    """Rendered blacklist data is loaded as sorted IP and network lists."""
    rendered = tmp_path / "ip_blacklist.txt"
    rendered.write_text("198.51.100.0/24\n192.0.2.9\nignored\n192.0.2.1\n")
    monkeypatch.setattr(utilities, "RENDERED_BLACKLIST", rendered)

    ips, nets = utilities.load_rendered_blacklist()

    assert ips == [ipa.ip_address("192.0.2.1"), ipa.ip_address("192.0.2.9")]
    assert nets == [ipa.ip_network("198.51.100.0/24")]


def test_get_public_ip_handles_success_invalid_and_request_failure(monkeypatch) -> None:
    """Public-IP lookup parses valid responses and suppresses request failures."""

    class Response:
        def __init__(self, text: str, *, raises: bool = False) -> None:
            self.text = text
            self.raises = raises

        def raise_for_status(self) -> None:
            if self.raises:
                raise RequestException("failed")

    monkeypatch.setattr(
        utilities.requests,
        "get",
        lambda _url: Response("192.0.2.4\n"),
    )
    assert utilities.get_public_ip() == ipa.ip_address("192.0.2.4")

    monkeypatch.setattr(utilities.requests, "get", lambda _url: Response("invalid"))
    assert utilities.get_public_ip() is None

    monkeypatch.setattr(
        utilities.requests,
        "get",
        lambda _url: SimpleNamespace(
            raise_for_status=lambda: (_ for _ in ()).throw(RequestException("failed"))
        ),
    )
    assert utilities.get_public_ip() is None


def test_clear_uses_platform_command(monkeypatch) -> None:
    """Screen clearing dispatches to the platform command."""
    commands: list[str] = []
    monkeypatch.setattr(utilities.os, "system", commands.append)
    monkeypatch.setattr(utilities.os, "name", "nt")

    utilities.clear()

    assert commands == ["cls"]
