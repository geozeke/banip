"""Rules for writing custom argument parsers.

1. Start with this sample argument parser, and modify it.
2. Make sure to give your file the same name as your command, but with
   the '_args' suffix (e.g. foo_args.py for the command defined by
   foo.py).
3. Do not change the function signature of the "load_command_args"
   function below.
4. The variable COMMAND_NAME below is required. It must contain the name
   of your command.
5. You may add additional functions/modules as needed. For example,
   adding something like "from argparse import FileType" if one of your
   commandline arguments is a file type.
6. Your code should return None.
7. Make sure to put this file in banip/src/plugins/argument_parsers.
"""

from argparse import _SubParsersAction

COMMAND_NAME = "foo"


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """This command takes two intergers on the command line, adds
    them together, then prints the result. Isn't that wonderful!"""
    parser = sp.add_parser(
        name=COMMAND_NAME,
        help=msg,
        description=msg,
    )

    msg = """The first variable to be added."""
    parser.add_argument(
        "first",
        type=int,
        help=msg,
    )

    msg = """This is the second."""
    parser.add_argument(
        "second",
        type=int,
        help=msg,
    )

    return
