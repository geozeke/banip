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
    Supported two-letter country code, case-insensitively. See
    https://geozeke.github.io/banip/country-codes/ for the complete
    reference.
    """
    parser.add_argument("country_code", type=str, help=msg)

    return


if __name__ == "__main__":
    pass
