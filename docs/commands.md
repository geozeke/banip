# Commands

Run `banip -h` to list commands and `banip <command> -h` for command
specific options.

## Build

```console
banip build
```

Build reads the selected countries, applies the allowlist and denylist,
optionally includes managed bot ranges, and writes:

```text
~/.banip/ip_blocklist.txt
~/.banip/ip_allowlist.txt
~/.banip/country_allowlist.txt
~/.banip/haproxy_geo_ip.txt
```

Use `--threshold` to set the minimum ipsum confidence score and
`--compact` to collapse sufficiently dense IPv4 `/24` ranges. Smaller
compaction values produce shorter blocklists but can block benign
addresses. Use `--no-bots` to exclude stored managed bot ranges from one
build.

## Check

```console
banip check
```

Enter an IP address to see its country, blocklist membership, and ipsum
feed status. The command requires an existing build because it reads the
rendered blocklist and country network map.

## Database

```console
banip database init
banip database status
banip database update
```

`init` creates the configuration and plugin directories. `status` shows
whether the required local files are present. `update` refreshes both
external data sources, or one named source when given `ipsum` or
`geolite`.

## Keep data current

MaxMind updates GeoLite2 Country data on Tuesdays and Fridays, while
`ipsum.txt` is updated daily. Schedule `banip database update` and then
`banip build` with cron or systemd to keep generated files current.
