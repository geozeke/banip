"""Argument parser for build command."""

from argparse import ArgumentTypeError
from argparse import FileType
from argparse import _SubParsersAction

COMMAND_NAME = "patch"


def threshold_type(x: str) -> int:
    """Validate the threshold input.

    Parameters
    ----------
    x : str
        User input for the threshold option.

    Returns
    -------
    int
        The validated user input.

    Raises
    ------
    argparse.ArgumentTypeError
        If the user input is not an integer type
    argparse.ArgumentTypeError
        If the user input is not within the acceptable range [1,10]
    """
    try:
        x_int = int(x)
    except ValueError:
        raise ArgumentTypeError("Threshold must be an integer")

    if x_int not in range(1, 11):
        raise ArgumentTypeError("Threshold must be between 1 and 10")

    return x_int


# ======================================================================


def load_command_args(sp: _SubParsersAction) -> None:
    """Assemble the argument parser."""
    msg = """
    Patch the ipsum.txt file with the contents of another list of IP
    addresses. Results will be de-duplicated, and only new entries will
    be added to ipsum.txt
    """
    parser = sp.add_parser(name=COMMAND_NAME, help=msg, description=msg)

    msg = """
    File containing additional IP addresses to augment ipsum.txt.
    """
    parser.add_argument("newips", type=FileType("r"), help=msg)

    msg = """
    Files of additional IP addesses must text files, where an IP address
    is located somewhere on each line. In addition to the IP address,
    there may be metadata or other items (e.g. comments) on each line.
    During processing, each line will be read, then split on space. Use
    the -i option to define which element in the list returned from
    split() to use to capture the IP address. The default is -1 (the
    last one).
    """
    parser.add_argument("-i", "--index", type=int, help=msg, default=-1)

    msg = """
    Each banned IP address in ipsum.txt has a factor (from 1 to 10)
    indicating a level of confidence that the IP address is a malicious
    actor (higher is more confident). Use this option to set the
    confidence factor of all the new IPs that you are adding to
    ipsum.txt. The default threshold used is 10.
    """
    parser.add_argument("-t", "--threshold", type=threshold_type, help=msg, default=10)

    return


if __name__ == "__main__":
    pass
