"""Argument parser for the bots command."""

import ipaddress as ipa
from argparse import _SubParsersAction

COMMAND_NAME = "bots"
PROVIDERS = ("google", "bing", "openai", "meta", "all")


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Refresh, inspect, and check managed crawler and bot provider IP
    ranges.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)
    subparsers = parser.add_subparsers(dest="action", required=True)

    msg = """
    Refresh managed CIDR ranges for one provider, or all known
    providers, into ~/.banip/botdata.json.
    """
    refresh = subparsers.add_parser(name="refresh", description=msg)
    refresh.add_argument("provider", choices=PROVIDERS, help=msg)

    msg = """
    List providers and range counts from ~/.banip/botdata.json.
    """
    subparsers.add_parser(name="list", description=msg)

    msg = """
    Check whether an IP address appears in stored managed bot ranges.
    """
    check = subparsers.add_parser(name="check", description=msg)
    check.add_argument("ip", type=ipa.ip_address, help=msg)

    return


if __name__ == "__main__":
    pass
