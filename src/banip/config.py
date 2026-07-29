"""Load, validate, and write banip YAML configuration."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from typing import cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq

from banip.constants import CONFIG
from banip.constants import LEGACY_CUSTOM_ALLOWLIST
from banip.constants import LEGACY_CUSTOM_DENYLIST
from banip.constants import TARGETS
from banip.constants import AddressType
from banip.constants import NetworkType
from banip.utilities import extract_ip

DEFAULT_BOT_PROVIDERS = ("google", "bing", "openai", "anthropic", "meta")
STARTER_PUBLIC_BLOCKLIST = ("CN", "RU")
STARTER_RESTRICTED_ALLOWLIST = ("CA", "US")
CONFIG_VERSION = 3
COUNTRY_POLICY_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


class CountryPolicyMode(StrEnum):
    """Supported country policy modes."""

    ALLOWLIST = "allowlist"
    BLOCKLIST = "blocklist"


@dataclass(frozen=True)
class CountryPolicy:
    """Validated country policy.

    Parameters
    ----------
    mode : CountryPolicyMode
        Whether configured country codes are allowed or blocked.
    codes : set[str]
        Normalized two-letter country codes.
    """

    mode: CountryPolicyMode
    codes: set[str]


@dataclass(frozen=True)
class CountryConfig:
    """Validated named country policies.

    Parameters
    ----------
    default_policy : str
        Policy used for the compatibility country allowlist.
    policies : dict[str, CountryPolicy]
        Policies keyed by their validated names.
    """

    default_policy: str
    policies: dict[str, CountryPolicy]


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
    countries : CountryConfig
        Named country policies used in builds.
    allowlist : set[AddressType | NetworkType]
        User-maintained entries that must not be blocked.
    denylist : set[AddressType | NetworkType]
        User-maintained entries to add to the blocklist.
    bots : BotConfig
        Managed bot range settings.
    """

    countries: CountryConfig
    allowlist: set[AddressType | NetworkType]
    denylist: set[AddressType | NetworkType]
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


def parse_country_codes(
    section: str,
    values: object,
    *,
    allow_empty: bool = False,
) -> set[str]:
    """Validate and normalize country codes.

    Parameters
    ----------
    section : str
        Configuration section name for validation messages.
    values : object
        Raw YAML country-code list.
    allow_empty : bool, optional
        Whether an empty country-code list is valid. Defaults to False.

    Returns
    -------
    set[str]
        Uppercase two-letter country codes.
    """
    if not isinstance(values, list):
        raise ValueError(f"Config section '{section}' must be a list.")
    if not values and not allow_empty:
        raise ValueError(f"Config section '{section}' must be a non-empty list.")

    countries: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"Invalid {section} entry: {value!r}")
        country = value.strip().upper()
        if len(country) != 2 or not country.isalpha():
            raise ValueError(f"Invalid {section} entry: {value!r}")
        countries.add(country)
    return countries


def parse_country_config(values: object) -> CountryConfig:
    """Validate and normalize named country policies.

    Parameters
    ----------
    values : object
        Raw YAML value from the ``countries`` section.

    Returns
    -------
    CountryConfig
        Validated country policy configuration.
    """
    if not isinstance(values, dict):
        raise ValueError("Config section 'countries' must be a mapping.")

    default_policy = values.get("default_policy")
    if not isinstance(default_policy, str):
        raise ValueError("Config entry 'countries.default_policy' must be a name.")

    raw_policies = values.get("policies")
    if not isinstance(raw_policies, dict) or not raw_policies:
        raise ValueError(
            "Config section 'countries.policies' must be a non-empty mapping."
        )

    policies: dict[str, CountryPolicy] = {}
    for name, raw_policy in raw_policies.items():
        if not isinstance(name, str) or not COUNTRY_POLICY_NAME.fullmatch(name):
            raise ValueError(f"Invalid country policy name: {name!r}")
        if not isinstance(raw_policy, dict):
            raise ValueError(
                f"Config section 'countries.policies.{name}' must be a mapping."
            )

        raw_mode = raw_policy.get("mode")
        if not isinstance(raw_mode, str):
            raise ValueError(f"Invalid country policy mode for {name!r}: {raw_mode!r}")
        try:
            mode = CountryPolicyMode(raw_mode)
        except ValueError:
            raise ValueError(
                f"Invalid country policy mode for {name!r}: {raw_mode!r}"
            ) from None

        section = f"countries.policies.{name}.codes"
        codes = parse_country_codes(
            section,
            raw_policy.get("codes"),
            allow_empty=mode is CountryPolicyMode.BLOCKLIST,
        )
        policies[name] = CountryPolicy(mode=mode, codes=codes)

    if default_policy not in policies:
        raise ValueError(f"Default country policy {default_policy!r} is not defined.")
    return CountryConfig(default_policy=default_policy, policies=policies)


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
            "documentation migration instructions."
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
    data = upgrade_config(load_raw_config(path), path)

    return BanipConfig(
        countries=parse_country_config(data.get("countries")),
        allowlist=parse_ip_entries("allowlist", data.get("allowlist")),
        denylist=parse_ip_entries("denylist", data.get("denylist")),
        bots=parse_bot_config(data.get("bots")),
    )


def upgrade_config(data: CommentedMap, path: Path) -> CommentedMap:
    """Upgrade a supported configuration schema in place.

    Parameters
    ----------
    data : CommentedMap
        Parsed YAML mapping.
    path : Path
        Path to rewrite after a successful upgrade.

    Returns
    -------
    CommentedMap
        The current-schema configuration mapping.

    Raises
    ------
    ValueError
        If the configuration schema is missing, unsupported, or mixes
        schema-version list keys.
    """
    version = data.get("version")
    if version not in {1, 2, CONFIG_VERSION}:
        raise ValueError(
            f"Unsupported config version: {version!r}. Expected version {CONFIG_VERSION}."
        )
    if version == CONFIG_VERSION:
        return data

    if version == 1:
        if "allowlist" in data or "denylist" in data:
            raise ValueError(
                "Config version 1 cannot mix allowlist or denylist "
                "with its prior list keys."
            )
        data["allowlist"] = data.pop("whitelist", CommentedSeq())
        data["denylist"] = data.pop("blacklist", CommentedSeq())

    if "countries" in data:
        raise ValueError(
            f"Config version {version} cannot mix targets with country policies."
        )

    targets = data.pop("targets", CommentedSeq())
    policy = CommentedMap(
        {
            "mode": CountryPolicyMode.ALLOWLIST.value,
            "codes": targets,
        }
    )
    countries = CommentedMap(
        {
            "default_policy": "restricted",
            "policies": CommentedMap({"restricted": policy}),
        }
    )
    data["countries"] = countries
    data["version"] = CONFIG_VERSION
    data.yaml_set_comment_before_after_key(
        "countries",
        before="Named country policies used to generate country allowlists.",
    )
    with path.open("w") as handle:
        yaml().dump(data, handle)
    return data


def read_migration_entries(path: Path) -> list[str]:
    """Read non-comment entries from a migration input file.

    Parameters
    ----------
    path : Path
        Migration input path.

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
    allowlist: Iterable[str] | None = None,
    denylist: Iterable[str] | None = None,
) -> CommentedMap:
    """Create starter YAML config data.

    Parameters
    ----------
    targets : Iterable[str] | None, optional
        Legacy target country codes to migrate. When omitted, create the
        documented restricted and public starter policies.
    allowlist : Iterable[str] | None, optional
        Entries that must not be blocked.
    denylist : Iterable[str] | None, optional
        Entries to add to the blocklist.

    Returns
    -------
    CommentedMap
        Starter config mapping.
    """
    data = CommentedMap()
    data["version"] = CONFIG_VERSION
    if targets is None:
        default_policy = "restricted"
        policies = CommentedMap(
            {
                "restricted": CommentedMap(
                    {
                        "mode": CountryPolicyMode.ALLOWLIST.value,
                        "codes": CommentedSeq(STARTER_RESTRICTED_ALLOWLIST),
                    }
                ),
                "public": CommentedMap(
                    {
                        "mode": CountryPolicyMode.BLOCKLIST.value,
                        "codes": CommentedSeq(STARTER_PUBLIC_BLOCKLIST),
                    }
                ),
            }
        )
    else:
        default_policy = "restricted"
        policies = CommentedMap(
            {
                "restricted": CommentedMap(
                    {
                        "mode": CountryPolicyMode.ALLOWLIST.value,
                        "codes": CommentedSeq(
                            sorted({item.upper() for item in targets})
                        ),
                    }
                )
            }
        )
    country_config = CommentedMap(
        {
            "default_policy": default_policy,
            "policies": policies,
        }
    )
    country_config.yaml_add_eol_comment(
        "Deprecated compatibility selector; removed in banip 3.0.",
        "default_policy",
    )
    data["countries"] = country_config
    data["allowlist"] = CommentedSeq(sorted(set(allowlist or [])))
    data["denylist"] = CommentedSeq(sorted(set(denylist or [])))
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
        "countries",
        before="Named country policies used to generate country allowlists.",
    )
    data.yaml_set_comment_before_after_key(
        "allowlist",
        before="Addresses or networks that should never be blocked.",
    )
    data.yaml_set_comment_before_after_key(
        "denylist",
        before="User-managed addresses or networks to add to the blocklist.",
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


def initialize_config(overwrite: bool = False, path: Path = CONFIG) -> None:
    """Create ``banip.yaml`` from prior flat configuration files.

    Parameters
    ----------
    overwrite : bool, optional
        Whether to replace an existing config file. Defaults to False.
    path : Path, optional
        Destination path. Defaults to ``CONFIG``.
    """
    if path.exists() and not overwrite:
        raise FileExistsError(f"Config file already exists: {path}")

    legacy_targets = read_migration_entries(TARGETS) if TARGETS.exists() else None
    data = config_template(
        targets=legacy_targets,
        allowlist=read_migration_entries(LEGACY_CUSTOM_ALLOWLIST),
        denylist=read_migration_entries(LEGACY_CUSTOM_DENYLIST),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        yaml().dump(data, handle)


def update_denylist(
    entries: Iterable[AddressType | NetworkType],
    path: Path = CONFIG,
) -> None:
    """Update the YAML ``denylist`` section.

    Parameters
    ----------
    entries : Iterable[AddressType | NetworkType]
        Parsed denylist entries to write.
    path : Path, optional
        Config file path. Defaults to ``CONFIG``.
    """
    data = load_raw_config(path)
    data["denylist"] = CommentedSeq(str(item) for item in entries)
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
