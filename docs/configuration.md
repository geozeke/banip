# Configuration

banip reads user-managed settings from `~/.banip/banip.yaml`.
`version`, `targets`, `allowlist`, and `denylist` are validated when
banip loads the configuration. The `bots` and `database` sections have
defaults when they are omitted.

```yaml
version: 2
targets:
  - US
allowlist: []
denylist: []
bots:
  enabled: true
  providers:
    - google
    - bing
    - openai
    - anthropic
    - meta
database:
  maxmind_edition: GeoLite2-Country-CSV
  secrets_file: ~/.secrets
```

## Targets

`targets` is a required list of two-letter country codes. banip considers
ipsum addresses only when their GeoLite2 country is in this list. See
[Country codes](country-codes.md) for the complete GeoNames-derived
reference.

## Allowlists and denylists

`allowlist` contains addresses or CIDR networks that must never be
blocked. `denylist` contains user-managed addresses or CIDR networks to
add to the rendered blocklist. Managed bot ranges are stored separately
in `botdata.json` rather than in `denylist`.

## Managed bots

`bots.enabled` controls whether builds include stored managed bot ranges
and defaults to `true`. `bots.providers` selects from `google`, `bing`,
`openai`, `anthropic`, and `meta`; all five are enabled by default. See
[Managed bot ranges](managed-bots.md) for refresh and inspection
commands.

## Automatic configuration upgrade

When banip reads a version-1 configuration, it automatically upgrades
the list keys and writes schema version 2. Do not mix version-1 and
version-2 list keys in one file; banip reports that ambiguity instead of
choosing a precedence.

## Database settings

`database.maxmind_edition` selects the MaxMind CSV edition and
`database.secrets_file` identifies an optional dotenv-style credential
file. The default values are `GeoLite2-Country-CSV` and `~/.secrets`.

The ipsum download URL can be overridden for mirrors or compatible
feeds:

```yaml
database:
  sources:
    ipsum:
      url: https://example.com/ipsum.txt
```

GeoLite downloads always use MaxMind's authenticated download endpoint
and the configured `database.maxmind_edition`.
