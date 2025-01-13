"""Argument parser for country command."""

from argparse import _SubParsersAction

COMMAND_NAME = "stats"


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Produce statistics for a given country code.
    """
    parser = sp.add_parser(name=COMMAND_NAME, help=msg, description=msg)
    msg = """
    This is the two-letter ISO-3166 ALPHA2 country code, not the
    two-letter Top Level Domain name (which may be different). For
    example, the two-letter TLD for the United Kingdom is "uk", but the
    ISO-3166 code for the United Kingdom is "gb". You can find a list of
    all the codes here: https://www.geonames.org/countries/
    """
    parser.add_argument("country_code", type=str, help=msg)

    return


if __name__ == "__main__":
    pass
