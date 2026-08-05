"""Task runner for the check command."""

import argparse
import ipaddress as ipa
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn
from rich.progress import Progress
from rich.progress import TaskProgressColumn
from rich.progress import TextColumn
from rich.table import Table
from rich.text import Text

from banip.config import CountryPolicy
from banip.config import CountryPolicyMode
from banip.config import load_config
from banip.constants import CONFIG
from banip.constants import COUNTRY_NETS_TXT
from banip.constants import IPSUM
from banip.constants import RENDERED_BLOCKLIST
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import NetworkLookup
from banip.utilities import build_network_lookup
from banip.utilities import ip_in_network
from banip.utilities import load_ipsum
from banip.utilities import load_rendered_blocklist
from banip.utilities import lookup_country


@dataclass(frozen=True)
class CheckData:
    """Prepared data used for IP address checks.

    Parameters
    ----------
    country_data_path : Path
        Path to the generated country network map.
    rendered_ips : frozenset[AddressType]
        Individual addresses in the rendered blocklist.
    rendered_lookup : NetworkLookup
        Lookup-ready networks in the rendered blocklist.
    ipsum : dict[AddressType, int]
        Ipsum confidence values keyed by address.
    country_policies : dict[str, CountryPolicy]
        Configured country policies keyed by name.
    """

    country_data_path: Path
    rendered_ips: frozenset[AddressType]
    rendered_lookup: NetworkLookup
    ipsum: dict[AddressType, int]
    country_policies: dict[str, CountryPolicy]


class CheckVerdict(StrEnum):
    """Possible combined IP blocklist and country-policy verdicts."""

    BLOCKED = "BLOCKED"
    NOT_BLOCKED = "NOT BLOCKED"
    POLICY_DEPENDENT = "POLICY DEPENDENT"
    COUNTRY_UNKNOWN = "COUNTRY UNKNOWN"


@dataclass(frozen=True)
class CheckResult:
    """Result of checking one IP address.

    Parameters
    ----------
    address : AddressType
        Address that was checked.
    country_code : str | None
        Associated country code, when available.
    blocklist_match : AddressType | NetworkType | None
        Exact address or network responsible for a blocked verdict.
    ipsum_confidence : int | None
        Exact ipsum confidence value, when available.
    blocked_policies : tuple[str, ...]
        Country policies that block the address country.
    permitted_policies : tuple[str, ...]
        Country policies that permit the address country.
    """

    address: AddressType
    country_code: str | None
    blocklist_match: AddressType | NetworkType | None
    ipsum_confidence: int | None
    blocked_policies: tuple[str, ...]
    permitted_policies: tuple[str, ...]

    @property
    def verdict(self) -> CheckVerdict:
        """Return the combined verdict across the available controls.

        Returns
        -------
        CheckVerdict
            Effective result or an indication that named policies differ.
        """
        if self.blocklist_match or (
            self.blocked_policies and not self.permitted_policies
        ):
            return CheckVerdict.BLOCKED
        if self.blocked_policies:
            return CheckVerdict.POLICY_DEPENDENT
        if not self.country_code:
            return CheckVerdict.COUNTRY_UNKNOWN
        return CheckVerdict.NOT_BLOCKED


def load_check_data(console: Console) -> CheckData:
    """Load and prepare data required by the check command.

    Parameters
    ----------
    console : Console
        Rich console used to display loading progress.

    Returns
    -------
    CheckData
        Prepared data for repeated address checks.
    """
    progress = Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    )
    with progress:
        task = progress.add_task("Loading configuration", total=3)
        config = load_config(CONFIG)
        progress.advance(task)

        progress.update(task, description="Loading ipsum data")
        ipsum = load_ipsum()
        progress.advance(task)

        progress.update(task, description="Loading rendered blocklist")
        rendered_ips, rendered_networks = load_rendered_blocklist()
        progress.advance(task)

        return CheckData(
            country_data_path=COUNTRY_NETS_TXT,
            rendered_ips=frozenset(rendered_ips),
            rendered_lookup=build_network_lookup(rendered_networks),
            ipsum=ipsum,
            country_policies=config.countries.policies,
        )


def check_address(address: AddressType, data: CheckData) -> CheckResult:
    """Check one address against prepared country and blocklist data.

    Parameters
    ----------
    address : AddressType
        Address to check.
    data : CheckData
        Prepared lookup data.

    Returns
    -------
    CheckResult
        Structured result for the address.
    """
    country_code = lookup_country(address, data.country_data_path)

    if address in data.rendered_ips:
        blocklist_match: AddressType | NetworkType | None = address
    else:
        blocklist_match = ip_in_network(address, data.rendered_lookup)

    blocked_policies: list[str] = []
    permitted_policies: list[str] = []
    if country_code:
        for name, policy in sorted(data.country_policies.items()):
            blocked = (
                country_code not in policy.codes
                if policy.mode is CountryPolicyMode.ALLOWLIST
                else country_code in policy.codes
            )
            if blocked:
                blocked_policies.append(name)
            else:
                permitted_policies.append(name)

    return CheckResult(
        address=address,
        country_code=country_code,
        blocklist_match=blocklist_match,
        ipsum_confidence=data.ipsum.get(address),
        blocked_policies=tuple(blocked_policies),
        permitted_policies=tuple(permitted_policies),
    )


def verdict_text(result: CheckResult) -> Text:
    """Return a styled textual verdict for a check result.

    Parameters
    ----------
    result : CheckResult
        Result to describe.

    Returns
    -------
    Text
        Styled blocked or not-blocked verdict.
    """
    if result.verdict is CheckVerdict.BLOCKED:
        return Text("BLOCKED", style="bold red")
    if result.verdict is CheckVerdict.NOT_BLOCKED:
        return Text("NOT BLOCKED", style="bold green")
    return Text(result.verdict, style="bold yellow")


def policy_text(result: CheckResult) -> Text:
    """Return a styled summary of country-policy decisions.

    Parameters
    ----------
    result : CheckResult
        Result to summarize.

    Returns
    -------
    Text
        Named blocked and permitted policies.
    """
    if not result.country_code:
        return Text("unavailable", style="yellow")

    summary = Text()
    if result.blocked_policies:
        summary.append("blocked: ", style="red")
        summary.append(", ".join(result.blocked_policies), style="bold red")
    if result.permitted_policies:
        if summary:
            summary.append("; ")
        summary.append("permitted: ", style="green")
        summary.append(", ".join(result.permitted_policies), style="bold green")
    return summary


def display_result(console: Console, result: CheckResult) -> None:
    """Display a detailed Rich card for one result.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    result : CheckResult
        Result to display.
    """
    details = Table.grid(padding=(0, 1))
    details.add_column(style="bold", justify="right")
    details.add_column()
    details.add_row("Verdict", verdict_text(result))
    details.add_row("Country", result.country_code or "—")
    details.add_row("Country policies", policy_text(result))
    details.add_row(
        "Blocklist match",
        str(result.blocklist_match) if result.blocklist_match else "—",
    )
    details.add_row(
        "ipsum confidence",
        f"{result.ipsum_confidence}/10" if result.ipsum_confidence is not None else "—",
    )
    if result.verdict is CheckVerdict.BLOCKED:
        border_style = "red"
    elif result.verdict is CheckVerdict.NOT_BLOCKED:
        border_style = "green"
    else:
        border_style = "yellow"
    console.print(
        Panel(
            details,
            title=f"IP Check: {result.address}",
            title_align="left",
            border_style=border_style,
            box=box.ROUNDED,
            expand=False,
        )
    )


def display_results(console: Console, results: list[CheckResult]) -> None:
    """Display a compact Rich table for multiple results.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    results : list[CheckResult]
        Results to display.
    """
    table = Table(
        title="Blocklist Check",
        title_style="bold cyan",
        box=box.ROUNDED,
        border_style="bright_black",
        header_style="bold",
        padding=(0, 1),
    )
    table.add_column("Address", style="cyan", min_width=15, overflow="fold")
    table.add_column("Verdict", overflow="fold")
    table.add_column("Country", no_wrap=True)
    table.add_column("Country policies", overflow="fold")
    table.add_column("Blocklist match", overflow="fold")
    table.add_column("ipsum confidence", justify="right")

    for result in results:
        table.add_row(
            str(result.address),
            verdict_text(result),
            result.country_code or "—",
            policy_text(result),
            str(result.blocklist_match) if result.blocklist_match else "—",
            f"{result.ipsum_confidence}/10"
            if result.ipsum_confidence is not None
            else "—",
        )
    console.print(table)


def interactive_check(console: Console, data: CheckData) -> None:
    """Prompt for and display address checks until the user exits.

    Parameters
    ----------
    console : Console
        Rich console used for output.
    data : CheckData
        Prepared lookup data.
    """
    while True:
        try:
            user_input = input("IP address (blank to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return

        if not user_input:
            return

        try:
            address = ipa.ip_address(user_input)
        except ValueError:
            console.print(Text(f"{user_input} is not a valid IP address.", style="red"))
            continue

        display_result(console, check_address(address, data))


def display_missing_data(console: Console) -> bool:
    """Display missing generated data and return whether any is absent.

    Parameters
    ----------
    console : Console
        Rich console used for output.

    Returns
    -------
    bool
        True when at least one required file is missing.
    """
    missing = [
        path
        for path in (CONFIG, COUNTRY_NETS_TXT, RENDERED_BLOCKLIST, IPSUM)
        if not path.exists()
    ]
    if not missing:
        return False

    paths = "\n".join(f"• {path}" for path in missing)
    console.print(
        Panel(
            f"Required build data is missing:\n{paths}\n\n"
            "Run [bold]banip build[/bold] before checking addresses.",
            title="Cannot check addresses",
            border_style="red",
            box=box.ROUNDED,
        )
    )
    return True


def task_runner(args: argparse.Namespace) -> None:
    """Display available data for one or more IP addresses.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments.
    """
    console = Console()
    if display_missing_data(console):
        return

    data = load_check_data(console)
    addresses: list[AddressType] = args.ip_addresses

    if not addresses:
        interactive_check(console, data)
    elif len(addresses) == 1:
        display_result(console, check_address(addresses[0], data))
    else:
        display_results(
            console,
            [check_address(address, data) for address in addresses],
        )
