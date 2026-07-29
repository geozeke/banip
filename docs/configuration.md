# Configuration

banip reads user-managed settings from `~/.banip/banip.yaml`.
`version`, `countries`, `allowlist`, and `denylist` are validated when
banip loads the configuration. The `bots` and `database` sections have
defaults when they are omitted.

```yaml
# Config schema version. Required.
version: 3
# Named country policies used to generate country allowlists.
countries:
  default_policy: restricted  # Deprecated compatibility selector; removed in banip 3.0.
  policies:
    restricted:
      mode: allowlist
      codes:
        - CA
        - US
    public:
      mode: blocklist
      codes:
        - CN
        - RU
# Addresses or networks that should never be blocked.
allowlist: []
# User-managed addresses or networks to add to the blocklist.
denylist: []
# Managed bot and crawler range settings.
bots:
  enabled: true
  providers:
    - google
    - bing
    - openai
    - anthropic
    - meta
# External database update settings.
database:
  maxmind_edition: GeoLite2-Country-CSV
  secrets_file: ~/.secrets
```

This is the starter configuration written by `banip database init`.
Review both example policies and select the country codes appropriate
for each consumer before building.

## Country policies

`countries.policies` contains one or more named policies. Policy names
start with a lowercase letter and may also contain lowercase letters,
digits, underscores, and hyphens.

An `allowlist` policy permits only its configured country codes. A
`blocklist` policy permits every country label in the current GeoLite2
data except its configured codes. An empty blocklist permits every
GeoLite2 country label; an allowlist must contain at least one code.
See [Country codes](country-codes.md) for the complete
GeoNames-derived reference.

Each build writes a positive country allowlist for every policy:

```text
~/.banip/country_allowlist_restricted.txt
~/.banip/country_allowlist_public.txt
```

These products always contain permitted codes, regardless of the
configured policy mode. This gives proxies and firewalls one consistent
membership check. `countries.default_policy` selects the policy also
written to `country_allowlist.txt` for compatibility with existing
consumers. Both the setting and compatibility file are deprecated,
remain supported throughout banip 2.x, and will be removed in banip
3.0. New integrations should use an explicitly named policy file. See
[Deprecations](deprecations.md#legacy-country-allowlist-output) for
migration guidance and the removal checklist.

The rendered IP blocklist includes qualifying threat addresses from the
union of countries permitted by all policies. A shared blocklist can
therefore protect services using different country policies. Addresses
without a GeoLite2 mapping are not included in a country policy.

Country geolocation is approximate. Use country policies as a
supplemental control rather than as authentication or authorization.

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

When banip reads a version-1 or version-2 configuration, it
automatically writes schema version 3. Existing `targets` become the
codes in a `restricted` allowlist policy, preserving the previous
country filter and threat-selection behavior. Version-1 list keys are
also renamed to their current forms.

Do not mix keys from different schema versions in one file. banip
reports the ambiguity instead of choosing a precedence.

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
