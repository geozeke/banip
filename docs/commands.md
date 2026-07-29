# Commands

Run `banip -h` or `banip --help` to list commands and
`banip <command> -h` for command-specific options. Use `banip -v` or
`banip --version` to print the installed version.

Except for `database init`, commands require the local directory
structure created by:

```console
banip database init
```

## Build

```console
banip build
```

Build resolves every named country policy, applies the IP allowlist and
denylist, optionally includes managed bot ranges, and writes:

```text
~/.banip/ip_blocklist.txt
~/.banip/ip_allowlist.txt
~/.banip/country_allowlist.txt
~/.banip/country_allowlist_<policy>.txt
~/.banip/haproxy_geo_ip.txt
```

The deprecated compatibility file `country_allowlist.txt` contains the
default policy and remains supported throughout banip 2.x. It will be
removed in banip 3.0 with the `countries.default_policy` setting. New
integrations should use an explicitly named policy file. Each named
policy file contains permitted country codes, including when the policy
was configured as a blocklist. The IP blocklist considers threat
addresses from countries permitted by any policy. See
[Deprecations](deprecations.md#legacy-country-allowlist-output) for
migration guidance.

The available options are:

- `-o FILE` or `--outfile FILE` selects an alternate blocklist output.
- `-t N` or `--threshold N` sets the minimum ipsum confidence score.
  The default is `3`, and valid values are `1` through `10`.
- `-c N` or `--compact N` collapses sufficiently dense IPv4 `/24`
  ranges. The default `0` disables compaction; valid enabled values are
  `1` through `255`. Smaller values produce shorter blocklists but can
  block benign addresses.
- `--no-bots` excludes stored managed bot ranges from one build.

## Bots

Refresh managed crawler and bot ranges for one provider:

```console
banip bots refresh google
```

The supported provider arguments are `google`, `bing`, `openai`,
`anthropic`, `meta`, and `all`. The `all` value refreshes every
provider.

Inspect or query the stored data with:

```console
banip bots list
banip bots check 192.0.2.1
```

See [Managed bot ranges](managed-bots.md) for configuration and build
behavior.

## Check

```console
banip check
```

Enter an IP address to see its country, blocklist membership, and ipsum
feed status. The command requires an existing build because it reads the
rendered blocklist and country network map. After each lookup, choose
whether to search again.

## Database

Initialize banip's local files:

```console
banip database init
```

Initialization creates the configuration and local data directories. It
also creates deprecated plugin directories during the banip 2.x
compatibility period. It imports existing flat configuration files when
present without deleting them. Use `--overwrite` to replace an existing
`~/.banip/banip.yaml`.

Inspect expected local data files:

```console
banip database status
```

Refresh both external sources, or choose one:

```console
banip database update
banip database update ipsum
banip database update geolite
```

The optional source argument is `all`, `ipsum`, or `geolite` and
defaults to `all`. GeoLite updates require MaxMind credentials.

## Patch

Add addresses from another text file to the local ipsum feed:

```console
banip patch new-addresses.txt
```

Each input line is split on whitespace. The last element is treated as
the address by default. Use `-i N` or `--index N` to select a different
zero-based element, including negative indexes such as `-1`.

New addresses receive confidence `10` by default. Use `-c N` or
`--confidence N` to choose a value from `1` through `10`. Existing
addresses are updated only when the requested confidence is higher.
Patching modifies `~/.banip/ipsum.txt`; a later
`banip database update ipsum` replaces that file with the downloaded
feed.

## Stats

```console
banip stats US
```

Stats accepts one two-letter country code, case-insensitively, and
reports IPv4 and IPv6 network and address totals. It requires an
existing build because it reads the generated country network map.

## Keep data current

MaxMind updates GeoLite2 Country data on Tuesdays and Fridays, while
`ipsum.txt` is updated daily. Schedule `banip database update` and then
`banip build` with cron or systemd to keep generated files current.
