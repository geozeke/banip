"""Load, validate, and write banip YAML configuration."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from typing import cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq

from banip.constants import CONFIG
from banip.constants import CUSTOM_BLACKLIST
from banip.constants import CUSTOM_WHITELIST
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip

DEFAULT_BOT_PROVIDERS = ("google", "bing", "openai", "anthropic", "meta")


@dataclass(frozen=True)
class BotConfig:
    """Managed bot range configuration.

    Parameters
    ----------
    enabled : bool
        Whether managed bot ranges are enabled for builds.
    providers : list[str]
        Provider keys to include.
    """

    enabled: bool
    providers: list[str]


@dataclass(frozen=True)
class BanipConfig:
    """Validated banip configuration.

    Parameters
    ----------
    targets : set[str]
        Uppercase country codes to include in builds.
    whitelist : set[AddressType | NetworkType]
        User-maintained whitelist entries.
    blacklist : set[AddressType | NetworkType]
        User-maintained blacklist entries.
    bots : BotConfig
        Managed bot range settings.
    """

    targets: set[str]
    whitelist: set[AddressType | NetworkType]
    blacklist: set[AddressType | NetworkType]
    bots: BotConfig


def yaml() -> YAML:
    """Create a configured YAML parser.

    Returns
    -------
    YAML
        A round-trip YAML parser.
    """
    parser = YAML()
    parser.default_flow_style = False
    parser.indent(mapping=2, sequence=4, offset=2)
    return parser


def parse_country_codes(values: object) -> set[str]:
    """Validate and normalize target country codes.

    Parameters
    ----------
    values : object
        Raw YAML value from the ``targets`` section.

    Returns
    -------
    set[str]
        Uppercase two-letter country codes.
    """
    if not isinstance(values, list) or not values:
        raise ValueError("Config section 'targets' must be a non-empty list.")

    countries: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"Invalid targets entry: {value!r}")
        country = value.strip().upper()
        if len(country) != 2 or not country.isalpha():
            raise ValueError(f"Invalid targets entry: {value!r}")
        countries.add(country)
    return countries


def parse_ip_entries(
    section: str,
    values: object,
) -> set[AddressType | NetworkType]:
    """Validate IP address and CIDR entries from one config section.

    Parameters
    ----------
    section : str
        Section name for error messages.
    values : object
        Raw YAML value.

    Returns
    -------
    set[AddressType | NetworkType]
        Parsed IP addresses and networks.
    """
    if values is None:
        return set()
    if not isinstance(values, list):
        raise ValueError(f"Config section '{section}' must be a list.")

    entries: set[AddressType | NetworkType] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"Invalid {section} entry: {value!r}")
        entry = extract_ip(value.strip())
        if not entry:
            raise ValueError(f"Invalid {section} entry: {value!r}")
        entries.add(entry)
    return entries


def parse_bot_config(values: object) -> BotConfig:
    """Validate managed bot configuration.

    Parameters
    ----------
    values : object
        Raw YAML value from the ``bots`` section.

    Returns
    -------
    BotConfig
        Normalized bot settings.
    """
    if values is None:
        return BotConfig(enabled=True, providers=list(DEFAULT_BOT_PROVIDERS))
    if not isinstance(values, dict):
        raise ValueError("Config section 'bots' must be a mapping.")

    enabled = values.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("Config entry 'bots.enabled' must be true or false.")

    providers = values.get("providers", list(DEFAULT_BOT_PROVIDERS))
    if not isinstance(providers, list) or not all(
        isinstance(provider, str) for provider in providers
    ):
        raise ValueError("Config entry 'bots.providers' must be a list of names.")

    return BotConfig(
        enabled=enabled,
        providers=[provider.strip().lower() for provider in providers],
    )


def load_raw_config(path: Path = CONFIG) -> CommentedMap:
    """Load raw YAML config data.

    Parameters
    ----------
    path : Path, optional
        Config file path. Defaults to ``CONFIG``.

    Returns
    -------
    CommentedMap
        Parsed YAML mapping.
    """
    if not path.exists():
        msg = (
            f"Missing config file: {path}\n"
            "Run 'banip database init' to create one, then review the "
            "README migration instructions."
        )
        raise FileNotFoundError(msg)

    data = yaml().load(path)
    if not isinstance(data, CommentedMap):
        raise ValueError("Config file must contain a YAML mapping.")
    return data


def load_config(path: Path = CONFIG) -> BanipConfig:
    """Load and validate ``banip.yaml``.

    Parameters
    ----------
    path : Path, optional
        Config file path. Defaults to ``CONFIG``.

    Returns
    -------
    BanipConfig
        Validated configuration.
    """
    data = load_raw_config(path)
    if "version" not in data:
        raise ValueError("Config entry 'version' is required.")

    return BanipConfig(
        targets=parse_country_codes(data.get("targets")),
        whitelist=parse_ip_entries("whitelist", data.get("whitelist")),
        blacklist=parse_ip_entries("blacklist", data.get("blacklist")),
        bots=parse_bot_config(data.get("bots")),
    )


def read_flat_entries(path: Path) -> list[str]:
    """Read non-comment entries from a legacy flat config file.

    Parameters
    ----------
    path : Path
        Legacy config path.

    Returns
    -------
    list[str]
        Non-empty, non-comment entries.
    """
    if not path.exists():
        return []
    return [
        token
        for line in path.read_text().splitlines()
        if (token := line.strip()) and not token.startswith("#")
    ]


def config_template(
    targets: Iterable[str] | None = None,
    whitelist: Iterable[str] | None = None,
    blacklist: Iterable[str] | None = None,
) -> CommentedMap:
    """Create starter YAML config data.

    Parameters
    ----------
    targets : Iterable[str] | None, optional
        Target country codes.
    whitelist : Iterable[str] | None, optional
        Whitelist entries.
    blacklist : Iterable[str] | None, optional
        Blacklist entries.

    Returns
    -------
    CommentedMap
        Starter config mapping.
    """
    data = CommentedMap()
    data["version"] = 1
    data["targets"] = CommentedSeq(sorted({item.upper() for item in targets or []}))
    data["whitelist"] = CommentedSeq(sorted(set(whitelist or [])))
    data["blacklist"] = CommentedSeq(sorted(set(blacklist or [])))
    data["bots"] = CommentedMap(
        {
            "enabled": True,
            "providers": CommentedSeq(DEFAULT_BOT_PROVIDERS),
        }
    )
    data["database"] = CommentedMap(
        {
            "maxmind_edition": "GeoLite2-Country-CSV",
            "secrets_file": "~/.secrets",
        }
    )

    data.yaml_set_start_comment("Config schema version. Required.")
    data.yaml_set_comment_before_after_key(
        "targets",
        before="Target countries included when building the rendered blacklist.",
    )
    data.yaml_set_comment_before_after_key(
        "whitelist",
        before="Addresses or networks that should never be blacklisted.",
    )
    data.yaml_set_comment_before_after_key(
        "blacklist",
        before="User-managed addresses or networks to add to the blacklist.",
    )
    data.yaml_set_comment_before_after_key(
        "bots",
        before="Managed bot and crawler range settings.",
    )
    data.yaml_set_comment_before_after_key(
        "database",
        before="External database update settings.",
    )
    return data


def migrate_flat_config(overwrite: bool = False, path: Path = CONFIG) -> None:
    """Create ``banip.yaml`` from legacy flat config files.

    Parameters
    ----------
    overwrite : bool, optional
        Whether to replace an existing config file. Defaults to False.
    path : Path, optional
        Destination path. Defaults to ``CONFIG``.
    """
    if path.exists() and not overwrite:
        raise FileExistsError(f"Config file already exists: {path}")

    data = config_template(
        targets=read_flat_entries(TARGETS),
        whitelist=read_flat_entries(CUSTOM_WHITELIST),
        blacklist=read_flat_entries(CUSTOM_BLACKLIST),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        yaml().dump(data, handle)


def update_blacklist(
    entries: Iterable[AddressType | NetworkType],
    path: Path = CONFIG,
) -> None:
    """Update the YAML ``blacklist`` section.

    Parameters
    ----------
    entries : Iterable[AddressType | NetworkType]
        Parsed blacklist entries to write.
    path : Path, optional
        Config file path. Defaults to ``CONFIG``.
    """
    data = load_raw_config(path)
    data["blacklist"] = CommentedSeq(str(item) for item in entries)
    with path.open("w") as handle:
        yaml().dump(data, handle)


def raw_config_dict(path: Path = CONFIG) -> dict[str, Any]:
    """Load config data for optional command settings.

    Parameters
    ----------
    path : Path, optional
        Config file path. Defaults to ``CONFIG``.

    Returns
    -------
    dict[str, Any]
        Raw config data, or an empty mapping when config is absent.
    """
    if not path.exists():
        return {}
    data = yaml().load(path)
    if not isinstance(data, dict):
        return {}
    return cast(dict[str, Any], data)
