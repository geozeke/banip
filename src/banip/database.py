"""Initialize and update external banip database files."""

import os
import shutil
import sys
import tempfile
import zipfile
from argparse import Namespace
from datetime import datetime
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from banip.config import initialize_config
from banip.config import load_config
from banip.constants import CONFIG
from banip.constants import CUSTOM_CODE
from banip.constants import CUSTOM_PARSERS
from banip.constants import DATA
from banip.constants import GEOLITE_4
from banip.constants import GEOLITE_6
from banip.constants import GEOLITE_LOC
from banip.constants import IPSUM

IPSUM_URL = "https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt"
MAXMIND_DOWNLOAD_URL = (
    "https://download.maxmind.com/geoip/databases/{edition}/download?suffix=zip"
)
REQUIRED_GEOLITE_FILES = (
    "GeoLite2-Country-Blocks-IPv4.csv",
    "GeoLite2-Country-Blocks-IPv6.csv",
    "GeoLite2-Country-Locations-en.csv",
)


def init_database(overwrite: bool = False) -> None:
    """Create the local data structure and starter config.

    Parameters
    ----------
    overwrite : bool, optional
        Whether to replace an existing config file. Defaults to False.

    """
    (DATA / "geolite").mkdir(parents=True, exist_ok=True)
    CUSTOM_CODE.mkdir(parents=True, exist_ok=True)
    CUSTOM_PARSERS.mkdir(parents=True, exist_ok=True)

    try:
        initialize_config(overwrite=overwrite, path=CONFIG)
    except FileExistsError as exc:
        print(exc)
        print("Use 'banip database init --overwrite' to replace it.")
        return

    print(f"Initialized {DATA}")
    print(f"Wrote {CONFIG}")


def update_ipsum() -> None:
    """Download the ipsum threat-intelligence feed."""
    settings = load_config(CONFIG).database
    url = settings.ipsum_url or IPSUM_URL
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    IPSUM.parent.mkdir(parents=True, exist_ok=True)
    IPSUM.write_text(response.text)
    print(f"Updated {IPSUM}")


def load_secrets(path: Path) -> None:
    """Load dotenv-style key-value secrets into the environment.

    Parameters
    ----------
    path : Path
        Secrets file path.

    """
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def maxmind_settings() -> tuple[str, str, str]:
    """Return MaxMind edition and credentials.

    Returns
    -------
    tuple[str, str, str]
        Edition, account ID, and license key.

    """
    settings = load_config(CONFIG).database
    if settings.secrets_file:
        load_secrets(Path(settings.secrets_file).expanduser())

    account_id = os.environ.get("MAXMIND_ACCOUNT_ID")
    license_key = os.environ.get("MAXMIND_LICENSE_KEY")
    if not account_id or not license_key:
        raise RuntimeError(
            "MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY are required for "
            "GeoLite updates."
        )
    return settings.maxmind_edition, account_id, license_key


def validate_geolite(path: Path) -> None:
    """Validate required GeoLite CSV files in an extracted directory.

    Parameters
    ----------
    path : Path
        Directory containing extracted files.

    """
    missing = [
        name
        for name in REQUIRED_GEOLITE_FILES
        if not any(candidate.name == name for candidate in path.rglob(name))
    ]
    if missing:
        raise RuntimeError(f"Missing GeoLite files: {', '.join(missing)}")


def replace_geolite(extracted: Path) -> None:
    """Atomically replace the local GeoLite directory.

    Parameters
    ----------
    extracted : Path
        Validated extracted GeoLite directory.

    """
    target = DATA / "geolite"
    replacement = DATA / "geolite.new"
    backup = DATA / "geolite.old"
    if replacement.exists():
        shutil.rmtree(replacement)
    replacement.mkdir(parents=True)
    for item in extracted.rglob("*"):
        if item.is_file():
            destination = replacement / item.name
            shutil.copy2(item, destination)

    if backup.exists():
        shutil.rmtree(backup)
    if target.exists():
        target.rename(backup)
    replacement.rename(target)
    if backup.exists():
        shutil.rmtree(backup)


def update_geolite() -> None:
    """Download, validate, and stage MaxMind GeoLite2 country data."""
    edition, account_id, license_key = maxmind_settings()
    url = MAXMIND_DOWNLOAD_URL.format(edition=edition)
    auth = (account_id, license_key)

    try:
        requests.head(url, auth=auth, allow_redirects=True, timeout=30)
    except requests.RequestException:
        pass

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / "geolite.zip"
        response = requests.get(url, auth=auth, allow_redirects=True, timeout=120)
        response.raise_for_status()
        zip_path.write_bytes(response.content)

        extract_path = temp_path / "extracted"
        extract_path.mkdir()
        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_path)
        except zipfile.BadZipFile as exc:
            raise RuntimeError(
                "Downloaded GeoLite archive is not a valid zip."
            ) from exc
        validate_geolite(extract_path)
        replace_geolite(extract_path)
    print(f"Updated {DATA / 'geolite'}")


def status() -> None:
    """Print local database status."""
    table = Table(
        title="Database Status",
        title_style="bold cyan",
        caption=f"Data directory: {DATA}",
        caption_style="dim",
        caption_justify="left",
        box=box.ROUNDED,
        border_style="bright_black",
        header_style="bold",
        padding=(0, 1),
    )
    table.add_column("Resource")
    table.add_column("Status")
    table.add_column("Last modified")
    resources = (
        ("Configuration", CONFIG),
        ("Ipsum threat feed", IPSUM),
        ("GeoLite IPv4 blocks", GEOLITE_4),
        ("GeoLite IPv6 blocks", GEOLITE_6),
        ("GeoLite country locations", GEOLITE_LOC),
    )
    for label, path in resources:
        if path.exists():
            modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
            table.add_row(
                label,
                Text("present", style="green"),
                Text(modified.strftime("%Y-%m-%d %H:%M:%S %Z"), style="cyan"),
            )
        else:
            table.add_row(
                label,
                Text("missing", style="bold red"),
                Text("—", style="dim"),
            )
    Console().print(table)


def task_runner(args: Namespace) -> None:
    """Run the selected database subcommand.

    Parameters
    ----------
    args : Namespace
        Command-line arguments.

    """
    try:
        if args.action == "init":
            init_database(overwrite=args.overwrite)
        elif args.action == "update":
            if args.source in ("all", "ipsum"):
                update_ipsum()
            if args.source in ("all", "geolite"):
                update_geolite()
        elif args.action == "status":
            status()
    except (OSError, RuntimeError, ValueError, requests.RequestException) as exc:
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    pass
