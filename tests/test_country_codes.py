"""Tests for country-code maintenance helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from banip.config import COUNTRY_CODES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts import check_country_codes  # noqa: E402


def country_row(code: str, name: str = "Fixture") -> str:
    """Return a minimal tab-delimited GeoNames country row."""
    return f"{code}\tXXX\t000\tXX\t{name}"


def test_parse_country_info_keeps_active_and_special_codes() -> None:
    """GeoNames comments and retired rows do not alter active support."""
    content = "\n".join(
        (
            "# GeoNames fixture",
            country_row("US", "United States"),
            country_row("XK", "Kosovo"),
            country_row("AN", "Netherlands Antilles"),
            country_row("CS", "Serbia and Montenegro"),
        )
    )

    assert check_country_codes.parse_country_info(content) == {"US", "XK"}


def test_parse_country_info_rejects_malformed_codes() -> None:
    """Malformed upstream rows fail instead of being silently ignored."""
    with pytest.raises(ValueError, match="Invalid GeoNames country code"):
        check_country_codes.parse_country_info(country_row("USA"))


def test_validate_country_codes_accepts_runtime_set() -> None:
    """The checked-in runtime set satisfies the maintenance validator."""
    check_country_codes.validate_country_codes(COUNTRY_CODES)


def test_validate_country_codes_reports_both_directions() -> None:
    """Drift reports missing upstream and unsupported local codes."""
    upstream = frozenset((COUNTRY_CODES - {"US"}) | {"ZZ"})

    with pytest.raises(ValueError) as exc_info:
        check_country_codes.validate_country_codes(upstream)

    message = str(exc_info.value)
    assert "Missing GeoNames country codes: ZZ" in message
    assert "Unsupported local country codes: US" in message
