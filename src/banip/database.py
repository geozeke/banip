"""Initialize and update external banip database files."""

import os
import shutil
import sys
import tempfile
import zipfile
from argparse import Namespace
from pathlib import Path
from typing import Any

import requests
from rich import box
from rich.console import Console
from rich.table import Table

from banip.config import migrate_flat_config
from banip.config import raw_config_dict
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
        migrate_flat_config(overwrite=overwrite, path=CONFIG)
    except FileExistsError as exc:
        print(exc)
        print("Use 'banip database init --overwrite' to replace it.")
        return

    print(f"Initialized {DATA}")
    print(f"Wrote {CONFIG}")


def config_section(name: str) -> dict[str, Any]:
    """Return one optional config section.

    Parameters
    ----------
    name : str
        Section name.

    Returns
    -------
    dict[str, Any]
        Config section data, or an empty mapping.
    """
    value = raw_config_dict().get(name, {})
    if isinstance(value, dict):
        return value
    return {}


def source_url(section: str, default: str) -> str:
    """Return a source URL from config overrides or a default.

    Parameters
    ----------
    section : str
        Source section name.
    default : str
        Built-in source URL.

    Returns
    -------
    str
        URL to use.
    """
    database = config_section("database")
    sources = database.get("sources", {})
    if not isinstance(sources, dict):
        return default
    source = sources.get(section, {})
    if not isinstance(source, dict):
        return default
    url = source.get("url", default)
    return url if isinstance(url, str) else default


def update_ipsum() -> None:
    """Download the ipsum threat-intelligence feed."""
    url = source_url("ipsum", IPSUM_URL)
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
    database = config_section("database")
    secrets_file = database.get("secrets_file", "~/.secrets")
    if isinstance(secrets_file, str):
        load_secrets(Path(secrets_file).expanduser())

    edition = database.get("maxmind_edition", "GeoLite2-Country-CSV")
    account_id = os.environ.get("MAXMIND_ACCOUNT_ID")
    license_key = os.environ.get("MAXMIND_LICENSE_KEY")
    if not isinstance(edition, str):
        edition = "GeoLite2-Country-CSV"
    if not account_id or not license_key:
        raise RuntimeError(
            "MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY are required for "
            "GeoLite updates."
        )
    return edition, account_id, license_key


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
    table = Table(title="Database Status", box=box.SQUARE)
    table.add_column("Path")
    table.add_column("Status")
    for path in [CONFIG, IPSUM, GEOLITE_4, GEOLITE_6, GEOLITE_LOC]:
        table.add_row(str(path), "present" if path.exists() else "missing")
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
    except (OSError, RuntimeError, requests.RequestException) as exc:
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    pass
