"""Display and terminal helpers."""

import os
from dataclasses import dataclass


def print_docstring(msg: str) -> None:
    """Print a formatted docstring.

    This function assumes the docstring is in a very specific format:

    >>> msg = \"\"\"
    >>> First line (non-blank)
    >>>
    >>> Subsequent lines
    >>> Subsequent lines
    >>> Subsequent lines
    >>> ...
    >>> Can include empty lines after the first.
    >>> \"\"\"

    Parameters
    ----------
    msg : str
        The docstring to be printed.
    """
    lines = msg.split("\n")[1:]
    spaces = 0
    for c in lines[0]:
        if c.isspace():
            spaces += 1
        else:
            break
    formatted_docstring = "\n".join([line[spaces:] for line in lines])
    print(formatted_docstring)
    return


@dataclass(frozen=True)
class StatusMessages:
    """Registry for keyed progress messages."""

    labels: dict[str, str]

    @property
    def max_label_length(self) -> int:
        """Return the length of the longest registered label."""
        return max(len(label) for label in self.labels.values())

    def label(self, key: str, **kwargs: object) -> str:
        """Return a formatted status label.

        Parameters
        ----------
        key : str
            Key for the registered status label.
        **kwargs : object
            Values used to format dynamic labels.

        Returns
        -------
        str
            The formatted status label.
        """
        return self.labels[key].format(**kwargs)

    def format(self, key: str, status: str = "✅", **kwargs: object) -> str:
        """Format a status line with aligned status values.

        Parameters
        ----------
        key : str
            Key for the registered status label.
        status : str, optional
            The status value. Defaults to a check mark.
        **kwargs : object
            Values used to format dynamic labels.

        Returns
        -------
        str
            The formatted status line.
        """
        label = self.label(key, **kwargs)
        target_length = max(self.max_label_length, len(label))
        leader = "." * max(target_length - len(label) + 3, 3)
        return f"{label}{leader}{status}"


STATUS_MESSAGES = StatusMessages(
    {
        "analyze": "Analyzing",
        "blacklist_rendered_load": "Loading rendered blacklist",
        "build_products": "Generating build products",
        "country_filter": "Filtering networks",
        "custom_prune": "Pruning custom blacklist",
        "geolite_load": "Loading geolocation data",
        "geo_pull": "Pulling country IDs",
        "geo_tag": "Geotagging networks",
        "ipsum_compact": "Compacting ipsum ({compact})",
        "ipsum_load": "Loading ipsum.txt",
        "ipsum_load_data": "Loading ipsum data",
        "ipsum_patch": "Patching with new IP addresses",
        "ipsum_prune": "Pruning ipsum.txt",
        "lists_render": "Rendering lists",
        "redundant_remove": "Removing redundant IP addresses",
        "repack": "Repackaging custom IP addresses",
        "stats_load": "Loading data",
    }
)


def status_label(key: str, **kwargs: object) -> str:
    """Return a status label by key.

    Parameters
    ----------
    key : str
        Key for the registered status label.
    **kwargs : object
        Values used to format dynamic labels.

    Returns
    -------
    str
        The formatted status label.
    """
    return STATUS_MESSAGES.label(key, **kwargs)


def format_status(key: str, status: str = "✅", **kwargs: object) -> str:
    """Format a status line with a minimum dot leader.

    Parameters
    ----------
    key : str
        Key for the registered status label.
    status : str, optional
        The status value. Defaults to a check mark.
    **kwargs : object
        Values used to format dynamic labels.

    Returns
    -------
    str
        The formatted status line.
    """
    return STATUS_MESSAGES.format(key, status, **kwargs)


def clear() -> None:
    """Clear the screen.

    This is an OS-agnostic version, which works with both Windows
    and Linux.
    """
    os.system("clear" if os.name == "posix" else "cls")
