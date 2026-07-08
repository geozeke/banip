"""Argument parser for the database command."""

from argparse import _SubParsersAction

COMMAND_NAME = "database"


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Initialize and update external banip data files.
    """
    parser = sp.add_parser(name=COMMAND_NAME, description=msg)
    subparsers = parser.add_subparsers(dest="action", required=True)

    msg = """
    Create the ~/.banip directory structure and create banip.yaml from
    existing flat config files when present.
    """
    init = subparsers.add_parser(name="init", description=msg)
    init.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing ~/.banip/banip.yaml.",
    )

    msg = """
    Download and stage external data files.
    """
    update = subparsers.add_parser(name="update", description=msg)
    update.add_argument(
        "source",
        nargs="?",
        choices=("all", "ipsum", "geolite"),
        default="all",
        help="External data source to update.",
    )

    msg = """
    Show whether expected local data files exist.
    """
    subparsers.add_parser(name="status", description=msg)

    return


if __name__ == "__main__":
    pass
