"""Regression tests for portable configuration and database files."""

from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from banip import config
from banip import database
from banip.utilities import data as utility_data


def test_unicode_config_replacement_preserves_comments(tmp_path) -> None:
    """UTF-8 CRLF configuration survives repeated atomic replacement."""
    path = tmp_path / "user café" / "banip.yaml"
    path.parent.mkdir()
    path.write_bytes(
        "# Deployment café 日本語\r\nversion: 2\r\n"
        "targets: [US]\r\nallowlist: []\r\ndenylist: []\r\n".encode("utf-8")
    )
    loaded = config.load_config(path)
    assert loaded.countries.policies["restricted"].codes == {"US"}
    for _ in range(2):
        config.write_config(config.load_raw_config(path), path)
        content = path.read_bytes()
        assert "# Deployment café 日本語\n".encode("utf-8") in content
        assert b"\r" not in content
        assert config.load_config(path) == loaded
    assert list(path.parent.glob(".banip.yaml.*")) == []


def test_geolite_directory_can_be_replaced_repeatedly(tmp_path, monkeypatch) -> None:
    """Windows-compatible staging replaces old files without leftovers."""
    data = tmp_path / "user café" / ".banip"
    target = data / "geolite"
    target.mkdir(parents=True)
    (target / "obsolete.csv").write_bytes(b"obsolete")
    extracted = tmp_path / "extracted" / "GeoLite"
    extracted.mkdir(parents=True)
    monkeypatch.setattr(database, "DATA", data)
    for revision in (b"first", b"second"):
        for name in database.REQUIRED_GEOLITE_FILES:
            (extracted / name).write_bytes(revision)
        database.validate_geolite(extracted.parent)
        database.replace_geolite(extracted.parent)
        assert not (target / "obsolete.csv").exists()
        for name in database.REQUIRED_GEOLITE_FILES:
            assert (target / name).read_bytes() == revision
        assert not (data / "geolite.new").exists()
        assert not (data / "geolite.old").exists()


def test_geolite_download_extracts_and_replaces_fixture(tmp_path, monkeypatch) -> None:
    """Mocked ZIP downloads update existing databases on every platform."""
    archive_bytes = BytesIO()
    with ZipFile(archive_bytes, "w") as archive:
        for name in database.REQUIRED_GEOLITE_FILES:
            archive.writestr(f"GeoLite/{name}", "header\r\nfixture\r\n")
    response = SimpleNamespace(
        content=archive_bytes.getvalue(), raise_for_status=lambda: None
    )
    data = tmp_path / "user café" / ".banip"
    data.mkdir(parents=True)
    monkeypatch.setattr(database, "DATA", data)
    monkeypatch.setattr(
        database, "maxmind_settings", lambda: ("GeoLite2-Country-CSV", "123", "key")
    )
    monkeypatch.setattr(database.requests, "head", lambda *args, **kwargs: response)
    monkeypatch.setattr(database.requests, "get", lambda *args, **kwargs: response)
    for _ in range(2):
        database.update_geolite()
        for name in database.REQUIRED_GEOLITE_FILES:
            assert (data / "geolite" / name).read_bytes() == b"header\r\nfixture\r\n"


def test_utf8_crlf_secrets_and_feed(tmp_path, monkeypatch) -> None:
    """Portable loaders accept Unicode comments and CRLF input."""
    secrets = tmp_path / "secrets café"
    secrets.write_bytes("# café 日本語\r\nBANIP_TEST_SECRET=value\r\n".encode("utf-8"))
    # Ensure the environment change is restored by pytest.
    monkeypatch.setenv("BANIP_TEST_SECRET", "")
    monkeypatch.delenv("BANIP_TEST_SECRET")
    database.load_secrets(secrets)
    assert database.os.environ["BANIP_TEST_SECRET"] == "value"
    feed = tmp_path / "ipsum.txt"
    feed.write_bytes("# café 日本語\r\n192.0.2.9 8\r\n".encode("utf-8"))
    monkeypatch.setattr(utility_data, "IPSUM", feed)
    assert {str(ip): hits for ip, hits in utility_data.load_ipsum().items()} == {
        "192.0.2.9": 8
    }
