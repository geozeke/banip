"""Argument parser for check command."""

from argparse import _SubParsersAction

COMMAND_NAME = "check"


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Check to see if a single IP address is found in the data generated
    from running \"banip build\". For example, if the IP resides in a
    country that is not part of targets.txt then it could show up in
    ipsum.txt, but will not show up in the rendered blacklist. The
    rendered blacklist only reflects those countries that are in
    targets.txt
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)

    msg = """
    This is the IPv4 or IPv6 address you're interested in. After you run
    \"banip build\", you can use the "check" command to see if a single
    IP address is found in the database. Making subsequent runs of banip
    to generate new data will use the updated information for future IP
    checking.
    """
    parser.add_argument("ip", type=str, help=msg)

    return
