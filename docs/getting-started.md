# Getting started

## Requirements

banip runs on macOS, Linux, and Windows Subsystem for Linux. Install
[uv](https://docs.astral.sh/uv/) and create a free or paid MaxMind
account with access to GeoLite2 Country CSV data.

## Install banip

```console
uv tool install --managed-python banip
```

Upgrade an existing installation with:

```console
uv tool upgrade banip
```

## Initialize local data

Create the local directory structure and starter configuration:

```console
banip database init
```

This writes `~/.banip/banip.yaml` and creates the local data
directories. During the banip 2.x compatibility period it also creates
the deprecated plugin directories. If the prior flat configuration
files exist, initialization imports their non-comment entries into the
new YAML configuration without deleting the source files.

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

Review the example restricted and public country policies in
`banip.yaml`, adjust their country codes, then run:

```console
banip build
```

The build writes:

```text
~/.banip/ip_blocklist.txt
~/.banip/ip_allowlist.txt
~/.banip/country_allowlist.txt
~/.banip/country_allowlist_restricted.txt
~/.banip/country_allowlist_public.txt
~/.banip/haproxy_geo_ip.txt
```

Additional named country policies produce corresponding
`country_allowlist_<policy>.txt` files. Use these named products for new
integrations. The unqualified `country_allowlist.txt` product is
deprecated and will be removed in banip 3.0.

See [Configuration](configuration.md) for the available settings and
[Commands](commands.md) for build options. Review
[Deprecations](deprecations.md) before planning a major-version
upgrade.
