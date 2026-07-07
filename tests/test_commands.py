"""Tests for command task runners."""

import argparse
import ipaddress as ipa
import pickle
from types import SimpleNamespace

import pytest

from banip import app
from banip import build
from banip import check
from banip import null
from banip import patch
from banip import stats
from banip import utilities
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
    monkeypatch.setattr(app, "CUSTOM_CODE", tmp_path / ".banip" / "plugins" / "code")
    monkeypatch.setattr(
        app,
        "CUSTOM_PARSERS",
        tmp_path / ".banip" / "plugins" / "parsers",
    )

    assert app.check_setup() is False
    assert "not configured correctly" in capsys.readouterr().out


def test_check_setup_accepts_required_directories(tmp_path, monkeypatch) -> None:
    """Setup validation passes when required local directories exist."""
    data = tmp_path / ".banip"
    custom_code = data / "plugins" / "code"
    custom_parsers = data / "plugins" / "parsers"
    geolite = data / "geolite"
    custom_code.mkdir(parents=True)
    custom_parsers.mkdir(parents=True)
    geolite.mkdir()
    monkeypatch.setattr(app, "DATA", data)
    monkeypatch.setattr(app, "CUSTOM_CODE", custom_code)
    monkeypatch.setattr(app, "CUSTOM_PARSERS", custom_parsers)

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
    monkeypatch.setattr(utilities, "IPSUM", ipsum)

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
    monkeypatch.setattr(stats, "COUNTRY_NETS_DICT", tmp_path / "missing.bin")

    stats.task_runner(argparse.Namespace(country_code="us"))

    assert "Run the 'build'" in capsys.readouterr().out


def test_stats_task_runner_reports_country_stats(tmp_path, monkeypatch, capsys) -> None:
    """Stats command summarizes IPv4 and IPv6 country data."""
    data = tmp_path / "country.bin"
    networks = {
        ipa.ip_network("192.0.2.0/30"): "US",
        ipa.ip_network("2001:db8::/126"): "US",
        ipa.ip_network("198.51.100.0/30"): "CA",
    }
    data.write_bytes(pickle.dumps(networks))
    monkeypatch.setattr(stats, "COUNTRY_NETS_DICT", data)

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
    data = tmp_path / "country.bin"
    data.write_bytes(pickle.dumps({ipa.ip_network("192.0.2.0/30"): "US"}))
    monkeypatch.setattr(stats, "COUNTRY_NETS_DICT", data)

    stats.task_runner(argparse.Namespace(country_code="zz"))

    assert "ZZ not found" in capsys.readouterr().out


def test_check_task_runner_handles_one_lookup(tmp_path, monkeypatch, capsys) -> None:
    """Check command loads generated data and handles one interactive lookup."""
    country_data = tmp_path / "country.bin"
    country_data.write_bytes(pickle.dumps({ipa.ip_network("192.0.2.0/24"): "US"}))
    rendered = tmp_path / "ip_blacklist.txt"
    rendered.write_text("192.0.2.0/28\n198.51.100.1\n")
    ipsum = tmp_path / "ipsum.txt"
    ipsum.write_text("192.0.2.3 7\n")
    inputs = iter(["invalid", "192.0.2.3", "n"])
    monkeypatch.setattr(check, "COUNTRY_NETS_DICT", country_data)
    monkeypatch.setattr(utilities, "RENDERED_BLACKLIST", rendered)
    monkeypatch.setattr(utilities, "IPSUM", ipsum)
    monkeypatch.setattr(check, "clear", lambda: None)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))

    check.task_runner(argparse.Namespace())

    output = capsys.readouterr().out
    assert utilities.format_status("ipsum_load_data") in output
    assert utilities.format_status("blacklist_rendered_load") in output
    assert utilities.format_status("geolite_load") in output
    assert "invalid is not a valid IP address." in output
    assert "Stats for 192.0.2.3" in output
    assert "found in subnet" in output


def test_check_task_runner_reports_missing_data(tmp_path, monkeypatch, capsys) -> None:
    """Check command prompts users to build data first."""
    monkeypatch.setattr(check, "COUNTRY_NETS_DICT", tmp_path / "missing.bin")

    check.task_runner(argparse.Namespace())

    assert "Run the 'build' command" in capsys.readouterr().out


def test_build_task_runner_generates_blacklist_outputs(
    tmp_path, monkeypatch, capsys
) -> None:
    """Build command filters source data into rendered output files."""
    data = tmp_path / ".banip"
    geolite = data / "geolite"
    geolite.mkdir(parents=True)
    paths = {
        "COUNTRY_WHITELIST": data / "country_whitelist.txt",
        "CUSTOM_BLACKLIST": data / "custom_blacklist.txt",
        "CUSTOM_WHITELIST": data / "custom_whitelist.txt",
        "GEOLITE_4": geolite / "GeoLite2-Country-Blocks-IPv4.csv",
        "GEOLITE_6": geolite / "GeoLite2-Country-Blocks-IPv6.csv",
        "GEOLITE_LOC": geolite / "GeoLite2-Country-Locations-en.csv",
        "IPSUM": data / "ipsum.txt",
        "RENDERED_BLACKLIST": data / "ip_blacklist.txt",
        "RENDERED_WHITELIST": data / "ip_whitelist.txt",
        "TARGETS": data / "targets.txt",
        "COUNTRY_NETS_TXT": data / "haproxy_geo_ip.txt",
        "COUNTRY_NETS_DICT": data / "haproxy_geo_ip_dict.bin",
    }
    paths["CUSTOM_BLACKLIST"].write_text("192.0.2.5\n192.0.2.0/30\n")
    paths["CUSTOM_WHITELIST"].write_text("192.0.2.4\n")
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
        "2001:db8::/126,1,1,,0,0,\n"
    )
    paths["IPSUM"].write_text("192.0.2.4 9\n192.0.2.9 8\n198.51.100.9 8\n")
    paths["TARGETS"].write_text("# comment\nus\n")
    for name, path in paths.items():
        if hasattr(build, name):
            monkeypatch.setattr(build, name, path)
        if hasattr(utilities, name):
            monkeypatch.setattr(utilities, name, path)
    monkeypatch.setattr(build, "get_public_ip", lambda: ipa.ip_address("203.0.113.10"))

    build.task_runner(argparse.Namespace(threshold=3, compact=0))

    output = capsys.readouterr().out
    assert utilities.format_status("redundant_remove") in output
    assert utilities.format_status("repack") in output
    assert "Compacting ipsum (0)" in output
    assert "0.00%" in output
    assert "Final Build Stats" in output
    assert paths["COUNTRY_WHITELIST"].read_text() == "US\n"
    assert paths["RENDERED_WHITELIST"].read_text() == "192.0.2.4\n"
    blacklist = paths["RENDERED_BLACKLIST"].read_text()
    assert "192.0.2.9" in blacklist
    assert "198.51.100.9" not in blacklist
    assert "192.0.2.0/30" in blacklist
