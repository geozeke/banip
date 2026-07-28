# Getting started

## Requirements

banip runs on macOS, Linux, and Windows Subsystem for Linux. Install
[uv](https://docs.astral.sh/uv/) and create a free or paid MaxMind
account with access to GeoLite2 Country CSV data.

## Install banip

```console
uv tool install --managed-python --from git+https://github.com/geozeke/banip.git@latest banip
```

## Initialize local data

Create the local directory structure and starter configuration:

```console
banip database init
```

This writes `~/.banip/banip.yaml` and creates plugin directories. If
the prior flat configuration files exist, initialization imports their
non-comment entries into the new YAML configuration without deleting the
source files.

## Download source data

Download the ipsum feed:

```console
banip database update ipsum
```

Set MaxMind credentials in the environment or in the dotenv-style file
named by `database.secrets_file` in `banip.yaml`:

```text
MAXMIND_ACCOUNT_ID=123456
MAXMIND_LICENSE_KEY=example
```

Then download the GeoLite2 Country CSV files:

```console
banip database update geolite
```

Run `banip database update` to refresh both sources.

## Build your first blocklist

Review `banip.yaml`, select at least one target country, then run:

```console
banip build
```

The resulting files are `~/.banip/ip_blocklist.txt` and
`~/.banip/ip_allowlist.txt`. See [Configuration](configuration.md) for
the available settings and [Commands](commands.md) for build options.
