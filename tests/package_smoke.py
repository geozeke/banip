"""Smoke-test an installed banip distribution artifact."""

from __future__ import annotations

import subprocess
import os
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory

import banip
import banip.app


def main() -> None:
    """Verify installed CLI behavior using isolated local fixture data."""
    package_version = version("banip")
    assert banip.__file__
    assert banip.app.__file__

    with TemporaryDirectory(prefix="banip-smoke-") as temporary_dir:
        home = Path(temporary_dir) / "Windows user café"
        home.mkdir()
        environment = os.environ.copy()
        environment.update(HOME=str(home), USERPROFILE=str(home))
        environment.pop("HOMEDRIVE", None)
        environment.pop("HOMEPATH", None)

        version_result = subprocess.run(
            ("banip", "--version"),
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        assert version_result.stdout.strip() == f"banip {package_version}"

        help_result = subprocess.run(
            ("banip", "--help"),
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "usage: banip" in help_result.stdout

        for arguments in (
            ("database", "init"),
            ("database", "init", "--overwrite"),
            ("database", "status"),
        ):
            subprocess.run(("banip", *arguments), env=environment, check=True)

        data = home / ".banip"
        assert (data / "banip.yaml").is_file()
        fixtures = {
            "GeoLite2-Country-Locations-en.csv": (
                "geoname_id,locale_code,continent_code,continent_name,"
                "country_iso_code,country_name,is_in_european_union\r\n"
                "1,en,NA,North America,US,United States,0\r\n"
            ),
            "GeoLite2-Country-Blocks-IPv4.csv": (
                "network,geoname_id,registered_country_geoname_id\r\n"
                "192.0.2.0/24,1,1\r\n"
            ),
            "GeoLite2-Country-Blocks-IPv6.csv": (
                "network,geoname_id,registered_country_geoname_id\r\n"
                "2001:db8::/32,1,1\r\n"
            ),
        }
        for name, content in fixtures.items():
            (data / "geolite" / name).write_bytes(content.encode("utf-8"))
        (data / "ipsum.txt").write_bytes(b"192.0.2.9 8\r\n2001:db8::9 8\r\n")
        output = home / "alternate blocklist.txt"
        subprocess.run(
            ("banip", "build", "--outfile", str(output)),
            env=environment,
            check=True,
        )
        # Exercise redirected output with a legacy Windows encoding too.
        environment["PYTHONIOENCODING"] = "cp1252"
        result = subprocess.run(
            ("banip", "build", "--outfile", str(output)),
            env=environment,
            check=True,
            capture_output=True,
        )
        assert b"Generating build products" in result.stdout
        assert b"192.0.2.9\n2001:db8::9\n" in output.read_bytes()
        assert output.read_bytes() == (data / "ip_blocklist.txt").read_bytes()
        for name in (
            "ip_blocklist.txt",
            "ip_allowlist.txt",
            "country_allowlist.txt",
            "country_allowlist_restricted.txt",
            "country_allowlist_public.txt",
            "haproxy_geo_ip.txt",
        ):
            assert (data / name).is_file()
            assert b"\r" not in (data / name).read_bytes()


if __name__ == "__main__":
    main()
