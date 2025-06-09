from argparse import ArgumentTypeError

# ======================================================================


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
        raise ArgumentTypeError("Value must be an integer")

    if x_int not in range(1, 11):
        raise ArgumentTypeError("Value must be between 1 and 10")

    return x_int


# ======================================================================


def compact_type(x: str) -> int:
    """Validate the compact input.

    Parameters
    ----------
    x : str
        User input for the compact option.

    Returns
    -------
    int
        The validated user input.

    Raises
    ------
    argparse.ArgumentTypeError
        If the user input is not an integer type
    argparse.ArgumentTypeError
        If the user input is not within the acceptable range [1,255]
    """
    try:
        x_int = int(x)
    except ValueError:
        raise ArgumentTypeError("Value must be an integer")

    if x_int not in range(1, 256):
        raise ArgumentTypeError("Value must be between 1 and 255")

    return x_int
