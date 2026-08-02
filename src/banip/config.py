"""Load, validate, and write banip YAML configuration."""

import copy
import re
import shutil
from tempfile import NamedTemporaryFile
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from typing import cast

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.error import YAMLError

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
DEFAULT_MAXMIND_EDITION = "GeoLite2-Country-CSV"
DEFAULT_SECRETS_FILE = "~/.secrets"
COUNTRY_CODES = frozenset(
    """
    AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ
    BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR
    CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR
    GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU
    ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ
    LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ
    MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF
    PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI
    SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR
    TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XK YE YT ZA ZM ZW
    """.split()
)


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
class DatabaseConfig:
    """Validated external database settings.

    Parameters
    ----------
    maxmind_edition : str
        MaxMind CSV edition used for authenticated downloads.
    secrets_file : str | None
        Optional dotenv-style credential file.
    ipsum_url : str | None
        Optional ipsum feed URL override.
    """

    maxmind_edition: str
    secrets_file: str | None
    ipsum_url: str | None


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
    database : DatabaseConfig
        External database update settings.
    """

    countries: CountryConfig
    allowlist: set[AddressType | NetworkType]
    denylist: set[AddressType | NetworkType]
    bots: BotConfig
    database: DatabaseConfig


def reject_unknown_keys(
    section: str,
    values: dict[object, object],
    allowed: set[str],
) -> None:
    """Reject unsupported configuration keys.

    Parameters
    ----------
    section : str
        Configuration section name.
    values : dict[object, object]
        Mapping to inspect.
    allowed : set[str]
        Supported keys.

    Raises
    ------
    ValueError
        If the mapping contains an unsupported key.
    """
    if unknown := sorted(str(key) for key in values if key not in allowed):
        raise ValueError(f"Unsupported config key in '{section}': {', '.join(unknown)}")


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
        if country not in COUNTRY_CODES:
            raise ValueError(f"Unknown {section} country code: {value!r}")
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
    reject_unknown_keys("countries", values, {"default_policy", "policies"})

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
        reject_unknown_keys(
            f"countries.policies.{name}",
            raw_policy,
            {"mode", "codes"},
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
    reject_unknown_keys("bots", values, {"enabled", "providers"})

    enabled = values.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("Config entry 'bots.enabled' must be true or false.")

    providers = values.get("providers", list(DEFAULT_BOT_PROVIDERS))
    if not isinstance(providers, list) or not all(
        isinstance(provider, str) for provider in providers
    ):
        raise ValueError("Config entry 'bots.providers' must be a list of names.")

    normalized = [provider.strip().lower() for provider in providers]
    if unknown := sorted(set(normalized) - set(DEFAULT_BOT_PROVIDERS)):
        raise ValueError(f"Unknown bot provider: {', '.join(unknown)}")
    if len(normalized) != len(set(normalized)):
        raise ValueError("Config entry 'bots.providers' contains duplicates.")

    return BotConfig(enabled=enabled, providers=normalized)


def parse_database_config(values: object) -> DatabaseConfig:
    """Validate external database settings.

    Parameters
    ----------
    values : object
        Raw YAML value from the ``database`` section.

    Returns
    -------
    DatabaseConfig
        Normalized database settings.
    """
    if values is None:
        return DatabaseConfig(
            maxmind_edition=DEFAULT_MAXMIND_EDITION,
            secrets_file=DEFAULT_SECRETS_FILE,
            ipsum_url=None,
        )
    if not isinstance(values, dict):
        raise ValueError("Config section 'database' must be a mapping.")
    reject_unknown_keys(
        "database",
        values,
        {"maxmind_edition", "secrets_file", "sources"},
    )

    edition = values.get("maxmind_edition", DEFAULT_MAXMIND_EDITION)
    if not isinstance(edition, str) or not edition.strip():
        raise ValueError("Config entry 'database.maxmind_edition' must be a name.")

    secrets_file = values.get("secrets_file", DEFAULT_SECRETS_FILE)
    if secrets_file is not None and (
        not isinstance(secrets_file, str) or not secrets_file.strip()
    ):
        raise ValueError("Config entry 'database.secrets_file' must be a path or null.")

    sources = values.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("Config section 'database.sources' must be a mapping.")
    reject_unknown_keys("database.sources", sources, {"ipsum"})
    ipsum = sources.get("ipsum", {})
    if not isinstance(ipsum, dict):
        raise ValueError("Config section 'database.sources.ipsum' must be a mapping.")
    reject_unknown_keys("database.sources.ipsum", ipsum, {"url"})
    ipsum_url = ipsum.get("url")
    if ipsum_url is not None and (
        not isinstance(ipsum_url, str) or not ipsum_url.strip()
    ):
        raise ValueError("Config entry 'database.sources.ipsum.url' must be a URL.")

    return DatabaseConfig(
        maxmind_edition=edition.strip(),
        secrets_file=secrets_file.strip() if isinstance(secrets_file, str) else None,
        ipsum_url=ipsum_url.strip() if isinstance(ipsum_url, str) else None,
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

    try:
        data = yaml().load(path)
    except YAMLError as exc:
        raise ValueError(f"Invalid YAML in config file {path}: {exc}") from exc
    if not isinstance(data, CommentedMap):
        raise ValueError("Config file must contain a YAML mapping.")
    return data


def parse_current_config(data: CommentedMap) -> BanipConfig:
    """Validate current-schema configuration data.

    Parameters
    ----------
    data : CommentedMap
        Current-schema YAML mapping.

    Returns
    -------
    BanipConfig
        Validated runtime configuration.
    """
    version = data.get("version")
    if type(version) is not int or version != CONFIG_VERSION:
        raise ValueError(
            f"Unsupported config version: {version!r}. Expected version {CONFIG_VERSION}."
        )
    reject_unknown_keys(
        "root",
        data,
        {"version", "countries", "allowlist", "denylist", "bots", "database"},
    )
    return BanipConfig(
        countries=parse_country_config(data.get("countries")),
        allowlist=parse_ip_entries("allowlist", data.get("allowlist")),
        denylist=parse_ip_entries("denylist", data.get("denylist")),
        bots=parse_bot_config(data.get("bots")),
        database=parse_database_config(data.get("database")),
    )


def write_config(data: CommentedMap, path: Path) -> None:
    """Atomically write validated YAML configuration data.

    Parameters
    ----------
    data : CommentedMap
        Validated current-schema mapping.
    path : Path
        Destination configuration file.
    """
    parse_current_config(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            yaml().dump(data, handle)
        if path.exists():
            shutil.copymode(path, temporary_path)
        temporary_path.replace(path)
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)


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
    return parse_current_config(data)


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
    if type(version) is not int or version not in {1, 2, CONFIG_VERSION}:
        raise ValueError(
            f"Unsupported config version: {version!r}. Expected version {CONFIG_VERSION}."
        )
    if version == CONFIG_VERSION:
        return data

    upgraded = copy.deepcopy(data)

    if version == 1:
        if "allowlist" in upgraded or "denylist" in upgraded:
            raise ValueError(
                "Config version 1 cannot mix allowlist or denylist "
                "with its prior list keys."
            )
        upgraded["allowlist"] = upgraded.pop("whitelist", CommentedSeq())
        upgraded["denylist"] = upgraded.pop("blacklist", CommentedSeq())

    if "countries" in upgraded:
        raise ValueError(
            f"Config version {version} cannot mix targets with country policies."
        )

    targets = upgraded.pop("targets", CommentedSeq())
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
    upgraded["countries"] = countries
    upgraded["version"] = CONFIG_VERSION
    upgraded.yaml_set_comment_before_after_key(
        "countries",
        before="Named country policies used to generate country allowlists.",
    )
    write_config(upgraded, path)
    return upgraded


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


def read_migration_country_codes(path: Path) -> list[str]:
    """Read valid country codes from a legacy targets file.

    Parameters
    ----------
    path : Path
        Legacy targets path.

    Returns
    -------
    list[str]
        Sorted, deduplicated country codes. Invalid legacy entries are
        ignored to preserve flat-file behavior.
    """
    codes = {
        normalized
        for value in read_migration_entries(path)
        if len(normalized := value.strip().upper()) == 2
        and normalized.isalpha()
        and normalized in COUNTRY_CODES
    }
    return sorted(codes)


def read_migration_ip_entries(path: Path) -> list[str]:
    """Read valid IP entries from a legacy list file.

    Parameters
    ----------
    path : Path
        Legacy allowlist or denylist path.

    Returns
    -------
    list[str]
        Sorted, deduplicated canonical entries. Invalid legacy entries
        are ignored to preserve flat-file behavior.
    """
    entries = {
        str(entry)
        for value in read_migration_entries(path)
        if (entry := extract_ip(value))
    }
    return sorted(entries)


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
            "maxmind_edition": DEFAULT_MAXMIND_EDITION,
            "secrets_file": DEFAULT_SECRETS_FILE,
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

    if path.exists():
        write_config(config_template(), path)
        return

    legacy_targets = read_migration_country_codes(TARGETS) if TARGETS.exists() else None
    if legacy_targets == []:
        raise ValueError(
            f"Legacy targets file contains no valid country codes: {TARGETS}"
        )
    data = config_template(
        targets=legacy_targets,
        allowlist=read_migration_ip_entries(LEGACY_CUSTOM_ALLOWLIST),
        denylist=read_migration_ip_entries(LEGACY_CUSTOM_DENYLIST),
    )
    write_config(data, path)


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
    data = copy.deepcopy(load_raw_config(path))
    data["denylist"] = CommentedSeq(str(item) for item in entries)
    write_config(data, path)


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
    return cast(dict[str, Any], load_raw_config(path))
