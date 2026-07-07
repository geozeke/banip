"""Argument parser for the stats command."""

from argparse import _SubParsersAction

COMMAND_NAME = "stats"


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Produce statistics for a country code.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)

    msg = """
    Two-letter ISO 3166-1 alpha-2 country code, not the two-letter
    top-level domain, which may be different. For example, the top-level
    domain for the United Kingdom is "uk", but its ISO 3166-1 alpha-2
    code is "gb". See https://www.geonames.org/countries/ for a list of
    country codes.
    """
    parser.add_argument("country_code", type=str, help=msg)

    return


if __name__ == "__main__":
    pass
