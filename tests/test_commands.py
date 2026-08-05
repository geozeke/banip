"""Tests for command task runners."""

import argparse
import ipaddress as ipa
import os
import re
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from banip import app
from banip import bots
from banip import build
from banip import check
from banip import config
from banip import database
from banip import null
from banip import patch
from banip import stats
from banip import utilities
from banip.utilities import data as utility_data
from banip.argument_types import compact_type
from banip.argument_types import threshold_type


def test_argument_types_accept_valid_values() -> None:
    """Custom argparse types return validated integers."""
    assert threshold_type("1") == 1
    assert threshold_type("10") == 10
    assert compact_type("1") == 1
    assert compact_type("255") == 255


@pytest.mark.parametrize(
    ("validator", "value", "message"),
    [
        (threshold_type, "x", "Value must be an integer"),
        (threshold_type, "11", "Value must be between 1 and 10"),
        (compact_type, "x", "Value must be an integer"),
        (compact_type, "0", "Value must be between 1 and 255"),
    ],
)
def test_argument_types_reject_invalid_values(
    validator, value: str, message: str
) -> None:
    """Custom argparse types raise useful errors for invalid input."""
    with pytest.raises(argparse.ArgumentTypeError, match=message):
        validator(value)


def test_check_setup_reports_missing_directories(tmp_path, monkeypatch, capsys) -> None:
    """Setup validation explains missing local directories."""
    monkeypatch.setattr(app, "DATA", tmp_path / ".banip")

    assert app.check_setup() is False
    assert "not configured correctly" in capsys.readouterr().out


def test_check_setup_accepts_required_directories(tmp_path, monkeypatch) -> None:
    """Setup validation does not require deprecated plugin directories."""
    data = tmp_path / ".banip"
    geolite = data / "geolite"
    geolite.mkdir(parents=True)
    monkeypatch.setattr(app, "DATA", data)

    assert app.check_setup() is True


def test_null_task_runner_prints_help_hint(capsys) -> None:
    """The null command prints a help hint."""
    null.task_runner(argparse.Namespace())

    assert "banip -h" in capsys.readouterr().out


def test_main_dispatches_to_null_command(monkeypatch) -> None:
    """No command dispatches to the null task runner."""
    called = False

    def fake_task_runner(_args) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(
        app,
        "importlib",
        SimpleNamespace(
            import_module=lambda _name: SimpleNamespace(task_runner=fake_task_runner)
        ),
    )
    monkeypatch.setattr(app, "collect_parsers", lambda _start: [])
    monkeypatch.setattr("sys.argv", ["banip"])

    assert app.main() == 0
    assert called is True


def test_main_reports_missing_custom_command_code(
    tmp_path, monkeypatch, capsys
) -> None:
    """Custom commands require matching code modules."""
    parser_dir = tmp_path / ".banip" / "plugins" / "parsers"
    parser_dir.mkdir(parents=True)
    (parser_dir / "custom_args.py").write_text(
        "COMMAND_NAME = 'custom'\n"
        "def load_command_args(sp):\n"
        "    sp.add_parser(name=COMMAND_NAME)\n"
    )
    monkeypatch.setattr(app, "ARG_PARSERS_BASE", tmp_path / "missing")
    monkeypatch.setattr(app, "CUSTOM_PARSERS", parser_dir)
    monkeypatch.setattr(app, "CUSTOM_CODE", tmp_path / "code")
    monkeypatch.setattr(app, "check_setup", lambda: True)
    monkeypatch.setattr("sys.argv", ["banip", "custom"])

    with pytest.raises(SystemExit) as exc_info:
        app.main()

    assert exc_info.value.code == 1
    assert "Code for a custom command" in capsys.readouterr().out


def test_patch_task_runner_updates_ipsum(tmp_path, monkeypatch, capsys) -> None:
    """Patch command adds new IPs and preserves higher confidence scores."""
    ipsum = tmp_path / "ipsum.txt"
    ipsum.write_text("192.0.2.1 9\n198.51.100.1 2\n")
    newips = tmp_path / "newips.txt"
    newips.write_text(
        "ignored 192.0.2.2\nignored 192.0.2.1\nblank\n\nignored invalid\n"
    )
    monkeypatch.setattr(patch, "IPSUM", ipsum)
    monkeypatch.setattr(utility_data, "IPSUM", ipsum)

    with newips.open() as handle:
        args = argparse.Namespace(newips=handle, index=1, confidence=5)
        patch.task_runner(args)

    output = capsys.readouterr().out
    assert utilities.format_status("ipsum_load") in output
    assert utilities.format_status("ipsum_patch") in output
    assert "New IP addresses added" in output
    assert ipsum.read_text().splitlines() == [
        "192.0.2.1 9",
        "198.51.100.1 2",
        "192.0.2.2 5",
    ]
    assert handle.closed


def test_patch_task_runner_exits_when_ipsum_missing(
    tmp_path, monkeypatch, capsys
) -> None:
    """Patch command reports a missing ipsum file."""
    missing = tmp_path / "missing.txt"
    monkeypatch.setattr(patch, "IPSUM", missing)

    with pytest.raises(SystemExit) as exc_info:
        patch.task_runner(argparse.Namespace(newips=[], index=-1, confidence=5))

    assert exc_info.value.code == 1
    assert "Missing file" in capsys.readouterr().out


def test_stats_task_runner_reports_missing_data(tmp_path, monkeypatch, capsys) -> None:
    """Stats command prompts users to build data first."""
    monkeypatch.setattr(stats, "COUNTRY_NETS_TXT", tmp_path / "missing.txt")

    stats.task_runner(argparse.Namespace(country_code="us"))

    assert "Run the 'build'" in capsys.readouterr().out


def test_stats_task_runner_reports_country_stats(tmp_path, monkeypatch, capsys) -> None:
    """Stats command summarizes IPv4 and IPv6 country data."""
    data = tmp_path / "haproxy_geo_ip.txt"
    data.write_text("192.0.2.0/30 US\n198.51.100.0/30 CA\n2001:db8::/126 US\n")
    monkeypatch.setattr(stats, "COUNTRY_NETS_TXT", data)
    monkeypatch.setattr(utility_data, "COUNTRY_NETS_TXT", data)

    stats.task_runner(argparse.Namespace(country_code="us"))

    output = capsys.readouterr().out
    assert utilities.format_status("stats_load") in output
    assert utilities.format_status("analyze") in output
    assert "Results for: US" in output
    assert "Networks (v4)" in output
    assert "Networks (v6)" in output


def test_stats_task_runner_reports_unknown_country(
    tmp_path, monkeypatch, capsys
) -> None:
    """Stats command reports an unknown country when no networks match."""
    data = tmp_path / "haproxy_geo_ip.txt"
    data.write_text("192.0.2.0/30 US\n")
    monkeypatch.setattr(stats, "COUNTRY_NETS_TXT", data)
    monkeypatch.setattr(utility_data, "COUNTRY_NETS_TXT", data)

    stats.task_runner(argparse.Namespace(country_code="zz"))

    assert "ZZ not found" in capsys.readouterr().out


def write_check_config(tmp_path: Path) -> Path:
    """Write a configuration with permitting and blocking policies.

    Parameters
    ----------
    tmp_path : Path
        Temporary directory in which to write the configuration.

    Returns
    -------
    Path
        Path to the written configuration.
    """
    config_file = tmp_path / "banip.yaml"
    config_file.write_text(
        "version: 3\n"
        "countries:\n"
        "  default_policy: restricted\n"
        "  policies:\n"
        "    restricted:\n"
        "      mode: allowlist\n"
        "      codes: [CA, US]\n"
        "    public:\n"
        "      mode: blocklist\n"
        "      codes: [CN]\n"
        "allowlist: []\n"
        "denylist: []\n"
    )
    return config_file


def test_check_task_runner_handles_one_lookup(tmp_path, monkeypatch, capsys) -> None:
    """Check command loads generated data and handles one interactive lookup."""
    country_data = tmp_path / "haproxy_geo_ip.txt"
    country_data.write_text("192.0.2.0/24 US\n")
    rendered = tmp_path / "ip_blocklist.txt"
    rendered.write_text("192.0.2.0/28\n198.51.100.1\n")
    ipsum = tmp_path / "ipsum.txt"
    ipsum.write_text("192.0.2.3 7\n")
    monkeypatch.setattr(check, "CONFIG", write_check_config(tmp_path))
    inputs = iter(["invalid", "192.0.2.3", ""])
    monkeypatch.setattr(check, "COUNTRY_NETS_TXT", country_data)
    monkeypatch.setattr(check, "RENDERED_BLOCKLIST", rendered)
    monkeypatch.setattr(check, "IPSUM", ipsum)
    monkeypatch.setattr(utility_data, "COUNTRY_NETS_TXT", country_data)
    monkeypatch.setattr(utility_data, "RENDERED_BLOCKLIST", rendered)
    monkeypatch.setattr(utility_data, "IPSUM", ipsum)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    check.task_runner(argparse.Namespace(ip_addresses=[]))

    output = capsys.readouterr().out
    assert "invalid is not a valid IP address." in output
    assert "IP Check: 192.0.2.3" in output
    assert "BLOCKED" in output
    assert "192.0.2.0/28" in output
    assert "7/10" in output


def test_check_task_runner_handles_batch_lookup(tmp_path, monkeypatch, capsys) -> None:
    """Check command renders multiple argument addresses in one table."""
    country_data = tmp_path / "haproxy_geo_ip.txt"
    country_data.write_text("192.0.2.0/24 US\n198.51.100.0/24 CA\n")
    rendered = tmp_path / "ip_blocklist.txt"
    rendered.write_text("192.0.2.0/28\n")
    ipsum = tmp_path / "ipsum.txt"
    ipsum.write_text("192.0.2.3 7\n198.51.100.8 4\n")
    monkeypatch.setattr(check, "CONFIG", write_check_config(tmp_path))
    monkeypatch.setattr(check, "COUNTRY_NETS_TXT", country_data)
    monkeypatch.setattr(check, "RENDERED_BLOCKLIST", rendered)
    monkeypatch.setattr(check, "IPSUM", ipsum)
    monkeypatch.setattr(utility_data, "COUNTRY_NETS_TXT", country_data)
    monkeypatch.setattr(utility_data, "RENDERED_BLOCKLIST", rendered)
    monkeypatch.setattr(utility_data, "IPSUM", ipsum)

    check.task_runner(
        argparse.Namespace(
            ip_addresses=[
                ipa.ip_address("192.0.2.3"),
                ipa.ip_address("198.51.100.8"),
            ]
        )
    )

    output = capsys.readouterr().out
    assert "Blocklist Check" in output
    assert "192.0.2.3" in output
    assert "BLOCKED" in output
    assert "198.51.100.8" in output
    assert "NOT BLOCKED" in output
    assert "CA" in output


def test_check_reports_country_policy_block(tmp_path, monkeypatch, capsys) -> None:
    """A country policy can block an address absent from the IP list."""
    country_data = tmp_path / "haproxy_geo_ip.txt"
    country_data.write_text("203.0.113.0/24 CN\n")
    rendered = tmp_path / "ip_blocklist.txt"
    rendered.write_text("")
    ipsum = tmp_path / "ipsum.txt"
    ipsum.write_text("")
    monkeypatch.setattr(check, "CONFIG", write_check_config(tmp_path))
    monkeypatch.setattr(check, "COUNTRY_NETS_TXT", country_data)
    monkeypatch.setattr(check, "RENDERED_BLOCKLIST", rendered)
    monkeypatch.setattr(check, "IPSUM", ipsum)
    monkeypatch.setattr(utility_data, "COUNTRY_NETS_TXT", country_data)
    monkeypatch.setattr(utility_data, "RENDERED_BLOCKLIST", rendered)
    monkeypatch.setattr(utility_data, "IPSUM", ipsum)

    check.task_runner(argparse.Namespace(ip_addresses=[ipa.ip_address("203.0.113.8")]))

    output = capsys.readouterr().out
    assert "BLOCKED" in output
    assert "CN" in output
    assert "blocked: public, restricted" in output
    assert "Blocklist match" in output


def test_check_reports_policy_dependent_result(tmp_path) -> None:
    """A country permitted by one policy and blocked by another is explicit."""
    country_data = tmp_path / "haproxy_geo_ip.txt"
    country_data.write_text("203.0.113.0/24 RU\n")
    data = check.CheckData(
        country_data_path=country_data,
        rendered_ips=frozenset(),
        rendered_lookup=utilities.build_network_lookup([]),
        ipsum={},
        country_policies={
            "public": config.CountryPolicy(
                mode=config.CountryPolicyMode.BLOCKLIST,
                codes={"CN"},
            ),
            "restricted": config.CountryPolicy(
                mode=config.CountryPolicyMode.ALLOWLIST,
                codes={"CA", "US"},
            ),
        },
    )

    result = check.check_address(ipa.ip_address("203.0.113.8"), data)

    assert result.verdict is check.CheckVerdict.POLICY_DEPENDENT
    assert result.blocked_policies == ("restricted",)
    assert result.permitted_policies == ("public",)


@pytest.mark.parametrize("error", [EOFError, KeyboardInterrupt])
def test_interactive_check_exits_on_terminal_signal(
    tmp_path, monkeypatch, error
) -> None:
    """Interactive checks handle terminal exit signals without a traceback."""
    data = check.CheckData(
        country_data_path=tmp_path / "haproxy_geo_ip.txt",
        rendered_ips=frozenset(),
        rendered_lookup=utilities.build_network_lookup([]),
        ipsum={},
        country_policies={},
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(error))

    check.interactive_check(check.Console(), data)


def test_check_task_runner_reports_missing_data(tmp_path, monkeypatch, capsys) -> None:
    """Check command prompts users to build data first."""
    monkeypatch.setattr(check, "CONFIG", tmp_path / "banip.yaml")
    monkeypatch.setattr(check, "COUNTRY_NETS_TXT", tmp_path / "missing.txt")
    monkeypatch.setattr(check, "RENDERED_BLOCKLIST", tmp_path / "blocklist.txt")
    monkeypatch.setattr(check, "IPSUM", tmp_path / "ipsum.txt")

    check.task_runner(argparse.Namespace(ip_addresses=[]))

    output = capsys.readouterr().out
    assert "Required build data is missing" in output
    assert "Run banip build" in output


def test_config_loads_and_validates_yaml(tmp_path, monkeypatch) -> None:
    """YAML config loads normalized runtime values."""
    path = tmp_path / "banip.yaml"
    path.write_text(
        "version: 2\n"
        "targets:\n"
        "  - us\n"
        "allowlist:\n"
        "  - 203.0.113.10\n"
        "denylist:\n"
        "  - 192.0.2.0/30\n"
        "bots:\n"
        "  enabled: false\n"
        "  providers:\n"
        "    - google\n"
    )
    monkeypatch.setattr(config, "CONFIG", path)

    loaded = config.load_config(path)

    assert loaded.countries.default_policy == "restricted"
    assert loaded.countries.policies["restricted"] == config.CountryPolicy(
        mode=config.CountryPolicyMode.ALLOWLIST,
        codes={"US"},
    )
    assert loaded.allowlist == {ipa.ip_address("203.0.113.10")}
    assert loaded.denylist == {ipa.ip_network("192.0.2.0/30")}
    assert loaded.bots.enabled is False
    assert loaded.bots.providers == ["google"]
    assert loaded.database.maxmind_edition == "GeoLite2-Country-CSV"
    assert loaded.database.secrets_file == "~/.secrets"
    assert loaded.database.ipsum_url is None


def test_config_defaults_include_managed_bot_providers() -> None:
    """Managed bot defaults include every built-in provider."""
    loaded = config.parse_bot_config(None)

    assert loaded.providers == ["google", "bing", "openai", "anthropic", "meta"]


@pytest.mark.parametrize(
    ("bots_config", "message"),
    [
        ({"providers": ["unknown"]}, "Unknown bot provider"),
        ({"providers": ["google", "GOOGLE"]}, "contains duplicates"),
        ({"enabled": True, "enable": False}, "Unsupported config key"),
    ],
)
def test_config_rejects_invalid_bot_settings(
    bots_config: object,
    message: str,
) -> None:
    """Bot configuration rejects names and keys that would be ignored."""
    with pytest.raises(ValueError, match=message):
        config.parse_bot_config(bots_config)


@pytest.mark.parametrize(
    ("database_config", "message"),
    [
        ({"maxmind_edition": 1}, "maxmind_edition"),
        ({"secrets_file": ""}, "secrets_file"),
        ({"sources": []}, "database.sources"),
        ({"sources": {"ipsum": {"url": 1}}}, "ipsum.url"),
        ({"source": {}}, "Unsupported config key"),
    ],
)
def test_config_rejects_invalid_database_settings(
    database_config: object,
    message: str,
) -> None:
    """Database configuration rejects malformed values and typos."""
    with pytest.raises(ValueError, match=message):
        config.parse_database_config(database_config)


def test_documented_starter_config_matches_generated_template() -> None:
    """The documented starter YAML matches database initialization."""
    rendered = StringIO()
    config.yaml().dump(config.config_template(), rendered)
    documentation = (
        Path(__file__).parents[1] / "docs" / "configuration.md"
    ).read_text()
    documented_yaml = documentation.split("```yaml", 1)[1].split("```", 1)[0]

    assert documented_yaml.strip() == rendered.getvalue().strip()


def test_initialize_config_uses_starter_policies_without_legacy_targets(
    tmp_path, monkeypatch
) -> None:
    """Fresh initialization creates the documented named policies."""
    path = tmp_path / "banip.yaml"
    monkeypatch.setattr(config, "TARGETS", tmp_path / "missing-targets.txt")
    monkeypatch.setattr(
        config,
        "LEGACY_CUSTOM_ALLOWLIST",
        tmp_path / "missing-allowlist.txt",
    )
    monkeypatch.setattr(
        config,
        "LEGACY_CUSTOM_DENYLIST",
        tmp_path / "missing-denylist.txt",
    )

    config.initialize_config(path=path)
    loaded = config.load_config(path)

    assert loaded.countries.default_policy == "restricted"
    assert loaded.countries.policies["restricted"].codes == {"CA", "US"}
    assert loaded.countries.policies["public"] == config.CountryPolicy(
        mode=config.CountryPolicyMode.BLOCKLIST,
        codes={"CN", "RU"},
    )


def test_config_parses_named_country_policies() -> None:
    """Named allowlist and blocklist policies are normalized."""
    loaded = config.parse_country_config(
        {
            "default_policy": "restricted",
            "policies": {
                "restricted": {
                    "mode": "allowlist",
                    "codes": ["us", "CA"],
                },
                "public": {
                    "mode": "blocklist",
                    "codes": [],
                },
            },
        }
    )

    assert loaded.default_policy == "restricted"
    assert loaded.policies["restricted"].codes == {"CA", "US"}
    assert loaded.policies["public"] == config.CountryPolicy(
        mode=config.CountryPolicyMode.BLOCKLIST,
        codes=set(),
    )


def test_country_code_reference_matches_config_validation() -> None:
    """The documented and accepted country-code sets remain synchronized."""
    reference = Path(__file__).parents[1] / "docs" / "country-codes.md"
    documented = set(re.findall(r"`([A-Z]{2})`", reference.read_text()))

    assert documented == config.COUNTRY_CODES


@pytest.mark.parametrize(
    ("countries", "message"),
    [
        (None, "countries.*mapping"),
        (
            {"default_policy": "default", "policies": {}},
            "countries.policies.*non-empty mapping",
        ),
        (
            {
                "default_policy": "default",
                "policies": {"../default": {"mode": "allowlist", "codes": ["US"]}},
            },
            "Invalid country policy name",
        ),
        (
            {
                "default_policy": "default",
                "policies": {"default": {"mode": "permit", "codes": ["US"]}},
            },
            "Invalid country policy mode",
        ),
        (
            {
                "default_policy": "default",
                "policies": {"default": {"mode": "allowlist", "codes": []}},
            },
            "must be a non-empty list",
        ),
        (
            {
                "default_policy": "default",
                "policies": {"default": {"mode": "allowlist", "codes": ["USA"]}},
            },
            "Invalid countries.policies.default.codes entry",
        ),
        (
            {
                "default_policy": "default",
                "policies": {"default": {"mode": "allowlist", "codes": ["ZZ"]}},
            },
            "Unknown countries.policies.default.codes country code",
        ),
        (
            {
                "default_policy": "missing",
                "policies": {"default": {"mode": "allowlist", "codes": ["US"]}},
            },
            "Default country policy.*not defined",
        ),
    ],
)
def test_config_rejects_invalid_country_policies(countries, message: str) -> None:
    """Malformed country policy structures fail with useful messages."""
    with pytest.raises(ValueError, match=message):
        config.parse_country_config(countries)


def test_config_rejects_invalid_denylist_entry(tmp_path) -> None:
    """Invalid YAML entries fail with section-specific messages."""
    path = tmp_path / "banip.yaml"
    path.write_text("version: 2\ntargets:\n  - US\ndenylist:\n  - nope\n")

    original = path.read_text()
    with pytest.raises(ValueError, match="Invalid denylist entry"):
        config.load_config(path)
    assert path.read_text() == original


def test_config_upgrades_version_one_lists(tmp_path) -> None:
    """Version-one configuration files upgrade to the current schema."""
    path = tmp_path / "banip.yaml"
    path.write_text(
        "version: 1\n"
        "targets:\n"
        "  - US\n"
        "whitelist:\n"
        "  - 203.0.113.10\n"
        "blacklist:\n"
        "  - 192.0.2.0/30\n"
    )

    loaded = config.load_config(path)

    assert loaded.allowlist == {ipa.ip_address("203.0.113.10")}
    assert loaded.denylist == {ipa.ip_network("192.0.2.0/30")}
    assert loaded.countries.policies["restricted"].codes == {"US"}
    upgraded = path.read_text()
    assert "version: 3" in upgraded
    assert "allowlist:" in upgraded
    assert "denylist:" in upgraded
    assert "countries:" in upgraded


def test_config_upgrades_version_two_country_targets(tmp_path) -> None:
    """Version-two targets become a restricted allowlist policy."""
    path = tmp_path / "banip.yaml"
    path.write_text(
        "# Keep this deployment note.\n"
        "version: 2\n"
        "targets:\n"
        "  - ca\n"
        "  - US\n"
        "allowlist: []\n"
        "denylist: []\n"
    )

    loaded = config.load_config(path)
    first_upgrade = path.read_text()
    loaded_again = config.load_config(path)

    assert loaded.countries.default_policy == "restricted"
    assert loaded.countries.policies["restricted"].codes == {"CA", "US"}
    assert loaded_again == loaded
    assert path.read_text() == first_upgrade
    assert first_upgrade.startswith("# Keep this deployment note.\n")
    assert "version: 3" in first_upgrade
    assert "targets:" not in first_upgrade


def test_config_rejects_mixed_schema_list_keys(tmp_path) -> None:
    """Mixed version-one and version-two list keys are rejected."""
    path = tmp_path / "banip.yaml"
    path.write_text("version: 1\ntargets:\n  - US\nallowlist: []\n")

    with pytest.raises(ValueError, match="cannot mix"):
        config.load_config(path)


@pytest.mark.parametrize("version_yaml", ["true", "1.0", "'1'"])
def test_config_rejects_noninteger_schema_versions(
    tmp_path,
    version_yaml: str,
) -> None:
    """Schema versions must be actual integers rather than equal values."""
    path = tmp_path / "banip.yaml"
    path.write_text(f"version: {version_yaml}\n")

    with pytest.raises(ValueError, match="Unsupported config version"):
        config.load_config(path)


def test_config_reports_malformed_yaml_as_a_value_error(tmp_path) -> None:
    """Malformed YAML produces a controlled configuration error."""
    path = tmp_path / "banip.yaml"
    path.write_text("version: [\n")

    with pytest.raises(ValueError, match="Invalid YAML in config file"):
        config.load_config(path)


def test_config_rejects_unknown_top_level_keys() -> None:
    """Top-level typos cannot be silently ignored."""
    data = config.config_template()
    data["botz"] = {}

    with pytest.raises(ValueError, match="Unsupported config key"):
        config.parse_current_config(data)


def test_database_init_migrates_legacy_flat_files(
    tmp_path, monkeypatch, capsys
) -> None:
    """Database init creates directories and migrates flat config files."""
    data = tmp_path / ".banip"
    monkeypatch.setattr(database, "DATA", data)
    monkeypatch.setattr(database, "CUSTOM_CODE", data / "plugins" / "code")
    monkeypatch.setattr(database, "CUSTOM_PARSERS", data / "plugins" / "parsers")
    monkeypatch.setattr(database, "CONFIG", data / "banip.yaml")
    monkeypatch.setattr(config, "CONFIG", data / "banip.yaml")
    monkeypatch.setattr(config, "TARGETS", data / "targets.txt")
    monkeypatch.setattr(
        config, "LEGACY_CUSTOM_ALLOWLIST", data / "custom_whitelist.txt"
    )
    monkeypatch.setattr(config, "LEGACY_CUSTOM_DENYLIST", data / "custom_blacklist.txt")
    data.mkdir()
    (data / "targets.txt").write_text("# comment\nus\n")
    (data / "custom_whitelist.txt").write_text("203.0.113.10\n")
    (data / "custom_blacklist.txt").write_text("192.0.2.0/30\n")

    database.init_database()

    output = capsys.readouterr().out
    assert "Initialized" in output
    assert (data / "geolite").exists()
    assert (data / "plugins" / "code").exists()
    assert "US" in (data / "banip.yaml").read_text()
    assert "203.0.113.10" in (data / "banip.yaml").read_text()
    assert "192.0.2.0/30" in (data / "banip.yaml").read_text()
    loaded = config.load_config(data / "banip.yaml")
    assert loaded.countries.default_policy == "restricted"
    assert loaded.countries.policies["restricted"].codes == {"US"}


def test_initialize_config_ignores_invalid_legacy_ip_entries(
    tmp_path,
    monkeypatch,
) -> None:
    """Legacy IP lists retain their prior invalid-line behavior."""
    path = tmp_path / "banip.yaml"
    targets = tmp_path / "targets.txt"
    allowlist = tmp_path / "custom_whitelist.txt"
    denylist = tmp_path / "custom_blacklist.txt"
    targets.write_text("US\n")
    allowlist.write_text("invalid\n203.0.113.10\n")
    denylist.write_text("also-invalid\n192.0.2.0/30\n")
    monkeypatch.setattr(config, "TARGETS", targets)
    monkeypatch.setattr(config, "LEGACY_CUSTOM_ALLOWLIST", allowlist)
    monkeypatch.setattr(config, "LEGACY_CUSTOM_DENYLIST", denylist)

    config.initialize_config(path=path)
    loaded = config.load_config(path)

    assert loaded.allowlist == {ipa.ip_address("203.0.113.10")}
    assert loaded.denylist == {ipa.ip_network("192.0.2.0/30")}
    assert "invalid" not in path.read_text()


def test_initialize_config_rejects_empty_legacy_targets(
    tmp_path,
    monkeypatch,
) -> None:
    """An empty legacy selection cannot create an invalid YAML file."""
    path = tmp_path / "banip.yaml"
    targets = tmp_path / "targets.txt"
    targets.write_text("# No selected countries\nnot-a-code\n")
    monkeypatch.setattr(config, "TARGETS", targets)
    monkeypatch.setattr(
        config,
        "LEGACY_CUSTOM_ALLOWLIST",
        tmp_path / "missing-allowlist.txt",
    )
    monkeypatch.setattr(
        config,
        "LEGACY_CUSTOM_DENYLIST",
        tmp_path / "missing-denylist.txt",
    )

    with pytest.raises(ValueError, match="no valid country codes"):
        config.initialize_config(path=path)

    assert not path.exists()


def test_initialize_config_overwrite_does_not_reimport_legacy_files(
    tmp_path,
    monkeypatch,
) -> None:
    """Overwrite creates a starter config independent of stale flat files."""
    path = tmp_path / "banip.yaml"
    path.write_text("existing configuration\n")
    targets = tmp_path / "targets.txt"
    targets.write_text("GB\n")
    monkeypatch.setattr(config, "TARGETS", targets)
    monkeypatch.setattr(
        config,
        "LEGACY_CUSTOM_ALLOWLIST",
        tmp_path / "missing-allowlist.txt",
    )
    monkeypatch.setattr(
        config,
        "LEGACY_CUSTOM_DENYLIST",
        tmp_path / "missing-denylist.txt",
    )

    config.initialize_config(overwrite=True, path=path)
    loaded = config.load_config(path)

    assert loaded.countries.policies["restricted"].codes == {"CA", "US"}
    assert "GB" not in path.read_text()


def test_database_status_reports_modification_times(tmp_path, monkeypatch) -> None:
    """Database status shows local modification times and missing files."""
    present = tmp_path / "banip.yaml"
    present.write_text("version: 3\n")
    missing = tmp_path / "ipsum.txt"
    timestamp = present.stat().st_mtime
    expected = (
        database.datetime.fromtimestamp(timestamp)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    monkeypatch.setattr(database, "CONFIG", present)
    monkeypatch.setattr(database, "IPSUM", missing)
    monkeypatch.setattr(database, "GEOLITE_4", tmp_path / "ipv4.csv")
    monkeypatch.setattr(database, "GEOLITE_6", tmp_path / "ipv6.csv")
    monkeypatch.setattr(database, "GEOLITE_LOC", tmp_path / "locations.csv")
    monkeypatch.setattr(database, "DATA", tmp_path)
    output_stream = StringIO()
    console = database.Console(
        file=output_stream,
        width=200,
        color_system=None,
    )
    monkeypatch.setattr(database, "Console", lambda: console)

    database.status()

    output = output_stream.getvalue()
    assert "Database Status" in output
    assert "Configuration" in output
    assert "Ipsum threat feed" in output
    assert "present" in output
    assert expected in output
    assert "missing" in output
    assert "—" in output
    assert "Data directory:" in output


def test_database_load_secrets_does_not_execute_shell(tmp_path, monkeypatch) -> None:
    """Secrets files are parsed as dotenv data."""
    secrets = tmp_path / ".secrets"
    secrets.write_text(
        "MAXMIND_ACCOUNT_ID=123\nMAXMIND_LICENSE_KEY='abc'\nignored line\n"
    )
    monkeypatch.delenv("MAXMIND_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("MAXMIND_LICENSE_KEY", raising=False)

    database.load_secrets(secrets)

    assert os.environ["MAXMIND_ACCOUNT_ID"] == "123"
    assert os.environ["MAXMIND_LICENSE_KEY"] == "abc"


def test_database_update_ipsum_uses_validated_url_override(
    tmp_path,
    monkeypatch,
) -> None:
    """Ipsum updates consume the validated database configuration."""

    class Response:
        """Successful feed response."""

        text = "192.0.2.1 5\n"

        def raise_for_status(self) -> None:
            """Accept the fake response."""

    seen = []
    settings = SimpleNamespace(ipsum_url="https://example.com/ipsum.txt")
    monkeypatch.setattr(
        database,
        "load_config",
        lambda _path: SimpleNamespace(database=settings),
    )
    monkeypatch.setattr(
        database.requests,
        "get",
        lambda url, timeout: seen.append((url, timeout)) or Response(),
    )
    ipsum = tmp_path / "ipsum.txt"
    monkeypatch.setattr(database, "IPSUM", ipsum)

    database.update_ipsum()

    assert seen == [("https://example.com/ipsum.txt", 60)]
    assert ipsum.read_text() == Response.text


def test_bots_normalize_ranges_deduplicates_and_sorts() -> None:
    """Provider payloads normalize into stable CIDR strings."""
    payloads = [
        {
            "prefixes": [
                {"ipv6Prefix": "2001:db8::/126"},
                {"ipv4Prefix": "198.51.100.0/24"},
                {"ipv4Prefix": "192.0.2.0/24"},
                {"ipv4Prefix": "192.0.2.0/24"},
            ]
        }
    ]

    assert bots.normalize_ranges(payloads) == [
        "192.0.2.0/24",
        "198.51.100.0/24",
        "2001:db8::/126",
    ]


def test_bots_parse_irr_ranges_deduplicates_and_sorts() -> None:
    """IRR route data normalizes into stable CIDR strings."""
    text = "\n".join(
        [
            "route:          198.51.100.0/24",
            "route:          192.0.2.0/24",
            "route:          192.0.2.0/24",
            "route6:         2001:db8::/48",
            "route6:         not-a-cidr",
            "origin:         AS32934",
        ]
    )

    assert bots.parse_irr_ranges(text) == [
        "192.0.2.0/24",
        "198.51.100.0/24",
        "2001:db8::/48",
    ]


def test_bots_fetch_provider_supports_meta_whois(monkeypatch) -> None:
    """Meta provider data is fetched from RADb WHOIS output."""
    monkeypatch.setattr(
        bots,
        "query_whois",
        lambda host, query: (
            "route:          192.0.2.0/24\nroute6:         2001:db8::/48\n"
        ),
    )

    entry = bots.fetch_provider("meta")

    assert entry["provider"] == "meta"
    assert entry["source"] == [bots.META_WHOIS_SOURCE]
    assert entry["ranges"] == ["192.0.2.0/24", "2001:db8::/48"]


def test_bots_fetch_provider_supports_anthropic_json(monkeypatch) -> None:
    """Anthropic provider data is fetched from its JSON feed."""

    class Response:
        """Fake JSON feed response."""

        def raise_for_status(self) -> None:
            """No-op successful status check."""

        def json(self) -> dict[str, object]:
            """Return provider payload data."""
            return {
                "creationTime": "2026-05-01T20:46:04Z",
                "prefixes": [
                    {"ipv4Prefix": "198.51.100.0/24"},
                    {"ipv4Prefix": "192.0.2.0/24"},
                ],
            }

    seen_urls = []

    def get(url: str, timeout: int) -> Response:
        seen_urls.append((url, timeout))
        return Response()

    monkeypatch.setattr(bots.requests, "get", get)

    entry = bots.fetch_provider("anthropic")

    assert seen_urls == [("https://claude.com/crawling/bots.json", 30)]
    assert entry["provider"] == "anthropic"
    assert entry["source"] == ["https://claude.com/crawling/bots.json"]
    assert entry["upstream_updated_at"] == "2026-05-01T20:46:04Z"
    assert entry["ranges"] == ["192.0.2.0/24", "198.51.100.0/24"]


def test_bots_refresh_replaces_only_selected_provider(
    tmp_path, monkeypatch, capsys
) -> None:
    """Refreshing one provider preserves other stored providers."""
    botdata = tmp_path / "botdata.json"
    botdata.write_text(
        "{\n"
        '  "providers": {\n'
        '    "bing": {\n'
        '      "provider": "bing",\n'
        '      "source": ["old"],\n'
        '      "refreshed_at": "old",\n'
        '      "ranges": ["198.51.100.0/24"]\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    monkeypatch.setattr(bots, "BOTDATA", botdata)
    monkeypatch.setattr(
        bots,
        "fetch_provider",
        lambda provider: {
            "provider": provider,
            "source": ["test"],
            "refreshed_at": "now",
            "ranges": ["192.0.2.0/24"],
        },
    )

    bots.refresh("google")

    data = bots.load_botdata()
    assert sorted(data["providers"]) == ["bing", "google"]
    assert data["providers"]["bing"]["ranges"] == ["198.51.100.0/24"]
    assert data["providers"]["google"]["ranges"] == ["192.0.2.0/24"]
    output = capsys.readouterr().out
    assert "Bot Range Refresh" in output
    assert "google" in output
    assert "1" in output
    assert "Saved to:" in output


def test_bots_list_providers_formats_stored_data(tmp_path, monkeypatch, capsys) -> None:
    """Bot provider listings use the shared summary presentation."""
    botdata = tmp_path / "botdata.json"
    botdata.write_text(
        "{\n"
        '  "providers": {\n'
        '    "google": {\n'
        '      "provider": "google",\n'
        '      "source": ["test"],\n'
        '      "refreshed_at": "2026-05-01T20:46:04+00:00",\n'
        '      "ranges": ["192.0.2.0/24"]\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    expected = bots.format_timestamp("2026-05-01T20:46:04+00:00")
    monkeypatch.setattr(bots, "BOTDATA", botdata)

    bots.list_providers()

    output = capsys.readouterr().out
    assert "Managed Bot Ranges" in output
    assert "google" in output
    assert "1" in output
    assert expected in output
    assert "Data file:" in output


def test_bots_list_providers_reports_empty_data(tmp_path, monkeypatch, capsys) -> None:
    """An empty bot data file produces an explicit empty-state row."""
    monkeypatch.setattr(bots, "BOTDATA", tmp_path / "botdata.json")

    bots.list_providers()

    output = capsys.readouterr().out
    assert "Managed Bot Ranges" in output
    assert "No stored providers" in output


def test_bots_check_ip_reports_matching_provider(tmp_path, monkeypatch, capsys) -> None:
    """Bot range checks report stored provider matches."""
    botdata = tmp_path / "botdata.json"
    botdata.write_text(
        "{\n"
        '  "providers": {\n'
        '    "google": {\n'
        '      "provider": "google",\n'
        '      "source": ["test"],\n'
        '      "refreshed_at": "now",\n'
        '      "ranges": ["192.0.2.0/24"]\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    monkeypatch.setattr(bots, "BOTDATA", botdata)

    bots.check_ip(ipa.ip_address("192.0.2.9"))

    output = capsys.readouterr().out
    assert "Managed Bot Check" in output
    assert "Address: 192.0.2.9" in output
    assert "google" in output
    assert "192.0.2.0/24" in output
    assert "found" in output


def test_bots_check_ip_reports_no_match(tmp_path, monkeypatch, capsys) -> None:
    """Bot range checks show a distinct not-found result."""
    monkeypatch.setattr(bots, "BOTDATA", tmp_path / "botdata.json")

    bots.check_ip(ipa.ip_address("198.51.100.9"))

    output = capsys.readouterr().out
    assert "Managed Bot Check" in output
    assert "Address: 198.51.100.9" in output
    assert "not found" in output


def test_build_task_runner_generates_blocklist_outputs(
    tmp_path, monkeypatch, capsys
) -> None:
    """Build command filters source data into rendered output files."""
    data = tmp_path / ".banip"
    geolite = data / "geolite"
    geolite.mkdir(parents=True)
    paths = {
        "COUNTRY_ALLOWLIST": data / "country_allowlist.txt",
        "GEOLITE_4": geolite / "GeoLite2-Country-Blocks-IPv4.csv",
        "GEOLITE_6": geolite / "GeoLite2-Country-Blocks-IPv6.csv",
        "GEOLITE_LOC": geolite / "GeoLite2-Country-Locations-en.csv",
        "IPSUM": data / "ipsum.txt",
        "RENDERED_BLOCKLIST": data / "ip_blocklist.txt",
        "RENDERED_ALLOWLIST": data / "ip_allowlist.txt",
        "TARGETS": data / "targets.txt",
        "COUNTRY_NETS_TXT": data / "haproxy_geo_ip.txt",
        "BOTDATA": data / "botdata.json",
        "CONFIG": data / "banip.yaml",
    }
    paths["CONFIG"].write_text(
        "version: 2\n"
        "targets:\n"
        "  - us\n"
        "  - US\n"
        "allowlist:\n"
        "  - 192.0.2.4\n"
        "  - 192.0.2.4\n"
        "denylist:\n"
        "  - 192.0.2.5\n"
        "  - 192.0.2.0/30\n"
    )
    paths["GEOLITE_LOC"].write_text(
        "geoname_id,locale_code,continent_code,continent_name,country_iso_code,"
        "country_name,is_in_european_union\n"
        "1,en,NA,North America,US,United States,0\n"
        "2,en,NA,North America,CA,Canada,0\n"
    )
    paths["GEOLITE_4"].write_text(
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider,postal_code\n"
        "198.51.100.0/24,2,2,,0,0,\n"
        "192.0.2.0/24,1,1,,0,0,\n"
    )
    paths["GEOLITE_6"].write_text(
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider,postal_code\n"
        "2001:db8::/126,1,1,,0,0,\n"
    )
    paths["IPSUM"].write_text("192.0.2.4 9\n192.0.2.9 8\n198.51.100.9 8\n")
    paths["TARGETS"].write_text("# comment\nus\nUS\n")
    for name, path in paths.items():
        if hasattr(build, name):
            monkeypatch.setattr(build, name, path)
        if hasattr(utility_data, name):
            monkeypatch.setattr(utility_data, name, path)
        if hasattr(bots, name):
            monkeypatch.setattr(bots, name, path)
        if hasattr(config, name):
            monkeypatch.setattr(config, name, path)
    alternate = data / "alternate_blocklist.txt"
    build.task_runner(
        argparse.Namespace(
            threshold=3,
            compact=0,
            outfile=alternate,
        )
    )

    output = capsys.readouterr().out
    assert utilities.format_status("redundant_remove") in output
    assert "Compacting ipsum (0)" in output
    assert "0.00%" in output
    assert "Final Build Summary" in output
    assert paths["COUNTRY_ALLOWLIST"].read_text() == "US\n"
    assert (data / "country_allowlist_restricted.txt").read_text() == "US\n"
    assert "192.0.2.5" in paths["CONFIG"].read_text()
    assert "192.0.2.0/30" in paths["CONFIG"].read_text()
    assert (
        paths["COUNTRY_NETS_TXT"].read_text()
        == "192.0.2.0/24 US\n198.51.100.0/24 CA\n2001:db8::/126 US\n"
    )
    assert paths["RENDERED_ALLOWLIST"].read_text() == "192.0.2.4\n"
    blocklist_lines = paths["RENDERED_BLOCKLIST"].read_text().splitlines()
    assert blocklist_lines[0] == "192.0.2.9"
    assert blocklist_lines[1] == ""
    assert blocklist_lines[2] == "# ------------custom entries -------------"
    assert blocklist_lines[3].startswith("# Added on: ")
    assert blocklist_lines[4:] == [
        "# ----------------------------------------",
        "",
        "192.0.2.5",
        "192.0.2.0/30",
    ]
    assert "198.51.100.9" not in blocklist_lines
    assert alternate.read_text() == paths["RENDERED_BLOCKLIST"].read_text()


def test_build_task_runner_generates_named_country_policies(
    tmp_path, monkeypatch, capsys
) -> None:
    """Build resolves named policies and uses their union for threats."""
    data = tmp_path / ".banip"
    geolite = data / "geolite"
    geolite.mkdir(parents=True)
    paths = {
        "COUNTRY_ALLOWLIST": data / "country_allowlist.txt",
        "GEOLITE_4": geolite / "GeoLite2-Country-Blocks-IPv4.csv",
        "GEOLITE_6": geolite / "GeoLite2-Country-Blocks-IPv6.csv",
        "GEOLITE_LOC": geolite / "GeoLite2-Country-Locations-en.csv",
        "IPSUM": data / "ipsum.txt",
        "RENDERED_BLOCKLIST": data / "ip_blocklist.txt",
        "RENDERED_ALLOWLIST": data / "ip_allowlist.txt",
        "COUNTRY_NETS_TXT": data / "haproxy_geo_ip.txt",
        "BOTDATA": data / "botdata.json",
        "CONFIG": data / "banip.yaml",
    }
    paths["CONFIG"].write_text(
        "version: 3\n"
        "countries:\n"
        "  default_policy: restricted\n"
        "  policies:\n"
        "    restricted:\n"
        "      mode: allowlist\n"
        "      codes:\n"
        "        - US\n"
        "    public:\n"
        "      mode: blocklist\n"
        "      codes:\n"
        "        - MX\n"
        "allowlist: []\n"
        "denylist: []\n"
        "bots:\n"
        "  enabled: false\n"
    )
    paths["GEOLITE_LOC"].write_text(
        "geoname_id,locale_code,continent_code,continent_name,country_iso_code,"
        "country_name,is_in_european_union\n"
        "1,en,NA,North America,US,United States,0\n"
        "2,en,NA,North America,CA,Canada,0\n"
    )
    paths["GEOLITE_4"].write_text(
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider,postal_code\n"
        "192.0.2.0/24,1,1,,0,0,\n"
        "198.51.100.0/24,2,2,,0,0,\n"
    )
    paths["GEOLITE_6"].write_text(
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider,postal_code\n"
        "2001:db8::/126,2,2,,0,0,\n"
    )
    paths["IPSUM"].write_text(
        "192.0.2.9 8\n198.51.100.9 8\n203.0.113.9 8\n2001:db8::1 8\n"
    )
    paths["RENDERED_BLOCKLIST"].touch()
    stale_policy = data / "country_allowlist_removed.txt"
    stale_policy.write_text("GB\n")
    unrelated_file = data / "country_allowlist_notes"
    unrelated_file.write_text("keep\n")

    for name, path in paths.items():
        if hasattr(build, name):
            monkeypatch.setattr(build, name, path)
        if hasattr(utility_data, name):
            monkeypatch.setattr(utility_data, name, path)
        if hasattr(bots, name):
            monkeypatch.setattr(bots, name, path)
        if hasattr(config, name):
            monkeypatch.setattr(config, name, path)
    build.task_runner(argparse.Namespace(threshold=3, compact=0, no_bots=False))

    output = capsys.readouterr().out
    assert paths["COUNTRY_ALLOWLIST"].read_text() == "US\n"
    assert (data / "country_allowlist_restricted.txt").read_text() == "US\n"
    assert (data / "country_allowlist_public.txt").read_text() == "CA\nUS\n"
    assert not stale_policy.exists()
    assert unrelated_file.read_text() == "keep\n"
    blocklist = paths["RENDERED_BLOCKLIST"].read_text()
    assert "192.0.2.9" in blocklist
    assert "198.51.100.9" in blocklist
    assert "2001:db8::1" in blocklist
    assert "203.0.113.9" not in blocklist
    assert "Country Policies" in output
    assert "public" in output
    assert "restricted (default)" in output
    assert "Threat scope" in output


def test_build_task_runner_renders_managed_bot_ranges(
    tmp_path, monkeypatch, capsys
) -> None:
    """Build command includes stored managed bot ranges by default."""
    data = tmp_path / ".banip"
    geolite = data / "geolite"
    geolite.mkdir(parents=True)
    paths = {
        "COUNTRY_ALLOWLIST": data / "country_allowlist.txt",
        "GEOLITE_4": geolite / "GeoLite2-Country-Blocks-IPv4.csv",
        "GEOLITE_6": geolite / "GeoLite2-Country-Blocks-IPv6.csv",
        "GEOLITE_LOC": geolite / "GeoLite2-Country-Locations-en.csv",
        "IPSUM": data / "ipsum.txt",
        "RENDERED_BLOCKLIST": data / "ip_blocklist.txt",
        "RENDERED_ALLOWLIST": data / "ip_allowlist.txt",
        "TARGETS": data / "targets.txt",
        "COUNTRY_NETS_TXT": data / "haproxy_geo_ip.txt",
        "BOTDATA": data / "botdata.json",
        "CONFIG": data / "banip.yaml",
    }
    config_text = (
        "version: 3\n"
        "countries:\n"
        "  default_policy: blocked\n"
        "  policies:\n"
        "    blocked:\n"
        "      mode: blocklist\n"
        "      codes:\n"
        "        - US\n"
        "allowlist:\n"
        "  - 198.51.100.9\n"
        "  - 203.0.113.1\n"
        "denylist:\n"
        "  - 198.51.100.9\n"
        "  - 198.51.100.10\n"
        "bots:\n"
        "  enabled: true\n"
        "  providers:\n"
        "    - google\n"
    )
    paths["CONFIG"].write_text(config_text)
    paths["GEOLITE_LOC"].write_text(
        "geoname_id,locale_code,continent_code,continent_name,country_iso_code,"
        "country_name,is_in_european_union\n"
        "1,en,NA,North America,US,United States,0\n"
    )
    paths["GEOLITE_4"].write_text(
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider,postal_code\n"
        "192.0.2.0/24,1,1,,0,0,\n"
    )
    paths["GEOLITE_6"].write_text(
        "network,geoname_id,registered_country_geoname_id,represented_country_geoname_id,"
        "is_anonymous_proxy,is_satellite_provider,postal_code\n"
    )
    paths["IPSUM"].write_text("192.0.2.9 8\n")
    paths["TARGETS"].write_text("US\n")
    paths["BOTDATA"].write_text(
        "{\n"
        '  "providers": {\n'
        '    "google": {\n'
        '      "provider": "google",\n'
        '      "source": ["test"],\n'
        '      "refreshed_at": "now",\n'
        '      "ranges": ["203.0.113.0/24"]\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    for name, path in paths.items():
        if hasattr(build, name):
            monkeypatch.setattr(build, name, path)
        if hasattr(utility_data, name):
            monkeypatch.setattr(utility_data, name, path)
        if hasattr(bots, name):
            monkeypatch.setattr(bots, name, path)
        if hasattr(config, name):
            monkeypatch.setattr(config, name, path)
    build.task_runner(argparse.Namespace(threshold=3, compact=0, no_bots=False))

    output = capsys.readouterr().out
    blocklist = paths["RENDERED_BLOCKLIST"].read_text()
    blocklist_entries = [
        token
        for line in blocklist.splitlines()
        if (token := utilities.extract_ip(line))
    ]
    blocklist_ips, blocklist_nets = utilities.split_hybrid(blocklist_entries)
    assert "Managed bots" in output
    assert "# ---------managed bot ranges -----------" in blocklist
    assert "# google\n" in blocklist
    assert ipa.ip_address("198.51.100.9") not in blocklist_ips
    assert ipa.ip_address("198.51.100.10") in blocklist_ips
    assert not utilities.ip_in_network(
        ipa.ip_address("203.0.113.1"),
        utilities.build_network_lookup(blocklist_nets),
    )
    assert utilities.ip_in_network(
        ipa.ip_address("203.0.113.2"),
        utilities.build_network_lookup(blocklist_nets),
    )
    assert paths["CONFIG"].read_text() == config_text


def test_apply_allowlist_splits_overlapping_networks() -> None:
    """Allowlisted space is removed from every blocked entry type."""
    blocked_ips = [
        ipa.ip_address("192.0.2.1"),
        ipa.ip_address("198.51.100.1"),
    ]
    blocked_nets = [
        ipa.ip_network("192.0.2.0/24"),
        ipa.ip_network("2001:db8::/126"),
    ]
    allowlist = {
        ipa.ip_address("192.0.2.1"),
        ipa.ip_network("2001:db8::/127"),
    }

    filtered_ips, filtered_nets = build.apply_allowlist(
        blocked_ips,
        blocked_nets,
        allowlist,
    )
    lookup = utilities.build_network_lookup(filtered_nets)

    assert filtered_ips == [ipa.ip_address("198.51.100.1")]
    assert not utilities.ip_in_network(ipa.ip_address("192.0.2.1"), lookup)
    assert utilities.ip_in_network(ipa.ip_address("192.0.2.2"), lookup)
    assert not utilities.ip_in_network(ipa.ip_address("2001:db8::1"), lookup)
    assert utilities.ip_in_network(ipa.ip_address("2001:db8::2"), lookup)
