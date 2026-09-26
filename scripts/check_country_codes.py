"""Compare supported country codes with the current GeoNames dataset."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlopen

from banip.config import COUNTRY_CODES

COUNTRY_INFO_URL = "https://download.geonames.org/export/dump/countryInfo.txt"
RETIRED_CODES = frozenset({"AN", "CS"})


def parse_country_info(content: str) -> frozenset[str]:
    """Extract active two-letter codes from GeoNames country information.

    Parameters
    ----------
    content : str
        UTF-8 text from the GeoNames ``countryInfo.txt`` dataset.

    Returns
    -------
    frozenset[str]
        Active country codes, excluding GeoNames' retired compatibility
        rows.

    Raises
    ------
    ValueError
        If a data row does not contain a two-letter country code.

    """
    codes: set[str] = set()
    for line in content.splitlines():
        if not line or line.startswith("#"):
            continue
        code = line.split("\t", 1)[0]
        if len(code) != 2 or not code.isascii() or not code.isalpha():
            raise ValueError(f"Invalid GeoNames country code row: {line!r}")
        codes.add(code.upper())
    return frozenset(codes - RETIRED_CODES)


def load_country_info(source: Path | None = None) -> str:
    """Load country information from a local file or GeoNames.

    Parameters
    ----------
    source : Path | None, optional
        Local dataset path. When omitted, download the current GeoNames
        dataset.

    Returns
    -------
    str
        Decoded country information.

    """
    if source:
        return source.read_text(encoding="utf-8")
    with urlopen(COUNTRY_INFO_URL, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8")


def validate_country_codes(upstream_codes: frozenset[str]) -> None:
    """Require runtime country codes to match active GeoNames entries.

    Parameters
    ----------
    upstream_codes : frozenset[str]
        Active country codes parsed from GeoNames.

    Raises
    ------
    ValueError
        If the runtime and upstream country-code sets differ.

    """
    problems: list[str] = []
    if missing := sorted(upstream_codes - COUNTRY_CODES):
        problems.append(f"Missing GeoNames country codes: {', '.join(missing)}")
    if extra := sorted(COUNTRY_CODES - upstream_codes):
        problems.append(f"Unsupported local country codes: {', '.join(extra)}")
    if problems:
        raise ValueError("\n".join(problems))


def main() -> None:
    """Load GeoNames country information and validate runtime support."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        help="Optional local countryInfo.txt path instead of a live download.",
    )
    args = parser.parse_args()
    try:
        codes = parse_country_info(load_country_info(args.source))
        validate_country_codes(codes)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"All {len(codes)} active GeoNames country codes are supported.")


if __name__ == "__main__":
    main()
