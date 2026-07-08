# Next Refactor

This TODO scopes the next major `banip` refactor. The goal is to make
three related workflows first-class:

- managed bot and crawler IP ranges,
- automated external database updates,
- centralized user-maintained configuration.

The old bot range rotation plan assumed bot refresh options would be
added directly to `banip build`. This plan replaces that direction.
Bot range management should move into a separate `banip bots` command,
while `banip build` should consume previously refreshed bot data.

## Summary

Add two new built-in commands:

- `banip bots` for refreshing, inspecting, and checking managed crawler
  and bot provider ranges.
- `banip database` for setting up and updating external data files such
  as `ipsum.txt` and MaxMind GeoLite2 country CSV data.

Add a centralized, user-editable YAML file at `~/.banip/banip.yaml`.
This file should become the preferred source of truth for target
countries, custom whitelist entries, custom blacklist entries, and
related preferences.

Existing flat files should continue to work while this refactor lands.
If `banip.yaml` is absent, `banip` should keep reading the current files:

- `~/.banip/targets.txt`,
- `~/.banip/custom_whitelist.txt`,
- `~/.banip/custom_blacklist.txt`.

## Command Architecture

Follow the existing built-in command pattern. Each new command needs a
parser module and a matching task module:

- `src/banip/parsers/bots_args.py`,
- `src/banip/bots.py`,
- `src/banip/parsers/database_args.py`,
- `src/banip/database.py`.

The dynamic parser loader in `app.py` already discovers built-in parser
modules under `src/banip/parsers/`. A command named `bots` should have a
parser module named `bots_args.py` and implementation code in
`src/banip/bots.py`.

Keep command-specific provider, storage, and download logic out of
`app.py`. The app module should remain responsible for parser loading,
setup checks, and dispatch.

## Bot Range Management

`banip bots` should own managed bot and crawler provider ranges. It
should refresh provider data into a reviewable JSON file and provide
basic inspection commands.

Initial user interface:

- `banip bots refresh PROVIDER`,
- `banip bots refresh all`,
- `banip bots list`,
- `banip bots check IP`.

Initial provider keys:

- `google`,
- `bing`,
- `openai`,
- `all` as a special command value for every known provider.

Provider names should be stable lowercase command values. Aliases can be
added later, but the first implementation should keep names explicit and
documented.

Meta crawlers remain a research item and should not be included in the
first implementation.

### Bot Storage

Use `~/.banip/botdata.json` as the source of truth for managed bot
ranges.

Store provider data in a reviewable structure grouped by provider key.
Each provider entry should include:

- provider key,
- source URL or local source label,
- last refreshed timestamp,
- normalized CIDR ranges,
- optional upstream creation or update timestamp when available.

Write `botdata.json` deterministically so diffs are stable. Sort
providers by key and ranges by IP version plus integer network address.

Refreshing one provider must replace only that provider's managed
ranges. It must not remove ranges for other providers already stored in
`botdata.json`.

If `botdata.json` does not exist, plain `banip build` should ignore it
and proceed without bot ranges. The file should be created only when a
refresh is requested.

Avoid pickle for first-class state. A pickle file is opaque, difficult
to review, and awkward to migrate.

### Provider Adapters

Do not assume every provider publishes clean JSON in the same shape. Use
provider-specific adapters that normalize provider data into the same
internal form:

- provider key,
- source metadata,
- deduplicated CIDR strings.

Initial adapters should handle JSON feeds with `prefixes` entries and
`ipv4Prefix` or `ipv6Prefix` keys.

Reference provider sources:

- Google crawler and fetcher IP range documentation:
  https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests
- Bingbot published ranges:
  https://www.bing.com/toolbox/bingbot.json
- OpenAI crawler documentation:
  https://developers.openai.com/api/docs/bots

Google documents multiple crawler and fetcher JSON feeds. Bing exposes a
`prefixes` JSON file. OpenAI publishes separate JSON files for
OAI-SearchBot, GPTBot, OAI-AdsBot, and ChatGPT-User.

### Build Integration

`banip build` should consume managed bot ranges but should not refresh
them.

During `banip build`:

- load `botdata.json` by default when it exists,
- skip bot loading when `--no-bots` is provided,
- treat a missing `botdata.json` as no managed bot ranges,
- parse stored CIDR ranges into `ipaddress` network objects,
- merge parsed bot ranges with other blacklist sources in memory,
- include those ranges in the final rendered blacklist,
- keep managed bot ranges logically separate from manual custom entries.

The final rendered blacklist should include a separate commented section
for managed bot ranges so users can see which entries came from bot
provider data.

Do not write bot ranges into `custom_blacklist.txt` or the future
`banip.yaml` custom blacklist section.

If bot ranges are loaded by default, the YAML config should allow that
default to be disabled:

```yaml
bots:
  enabled: true
  providers:
    - google
    - bing
    - openai
```

## Database Management

`banip database` should own setup and automated refresh of external
source files that users currently download and stage manually.

Initial user interface:

- `banip database init`,
- `banip database update`,
- `banip database update ipsum`,
- `banip database update geolite`,
- `banip database status`.

`init` should create the expected local directory structure:

```text
~/.banip
├── geolite
└── plugins
    ├── code
    └── parsers
```

It should also be able to create a starter `~/.banip/banip.yaml`.

`update` should download and stage:

- ipsum threat-intelligence data to `~/.banip/ipsum.txt`,
- MaxMind GeoLite2 Country CSV data to `~/.banip/geolite`.

The ipsum source should remain the upstream raw feed:

```text
https://raw.githubusercontent.com/stamparm/ipsum/master/ipsum.txt
```

MaxMind CSV clients must use direct download. The command should use
Basic Auth with the account ID and license key, follow redirects, and
download the GeoLite2 Country CSV zip. MaxMind recommends checking the
`Last-Modified` header with a `HEAD` request before downloading where
practical. Existing database links may redirect to MaxMind's R2-backed
download host.

For MaxMind updates:

- read credentials from environment variables,
- optionally load those variables from a dotenv-style `~/.secrets` file,
- issue a `HEAD` request when possible to check for changes,
- download the zip to a temporary path,
- extract into a temporary directory,
- validate required GeoLite2 country CSV files,
- atomically replace `~/.banip/geolite` only after validation succeeds.

Required extracted files should include at least:

- `GeoLite2-Country-Blocks-IPv4.csv`,
- `GeoLite2-Country-Blocks-IPv6.csv`,
- `GeoLite2-Country-Locations-en.csv`.

Other location, copyright, and license files may also be present and
should be preserved.

### Credential Policy

Do not store MaxMind secrets in `~/.banip/banip.yaml`.

Credentials should come from:

- `MAXMIND_ACCOUNT_ID`,
- `MAXMIND_LICENSE_KEY`.

`banip database` should support loading a simple dotenv-style
`~/.secrets` file before reading the environment:

```text
MAXMIND_ACCOUNT_ID=123456
MAXMIND_LICENSE_KEY=example
```

The secrets file must be parsed as key-value data, not executed as shell
code.

The YAML config may point to the secrets file path:

```yaml
database:
  maxmind_edition: GeoLite2-Country-CSV
  secrets_file: ~/.secrets
```

## Centralized YAML Configuration

Add `~/.banip/banip.yaml` as the preferred source of truth for
user-maintained data.

Use YAML because the end user needs to edit data and metadata directly
as the format evolves. Add a YAML dependency that can preserve comments
and ordering when writing, such as `ruamel.yaml`.

Initial shape:

```yaml
version: 1

targets:
  - US
  - CA

whitelist:
  - 203.0.113.10

blacklist:
  - 192.0.2.5
  - 192.0.2.0/30

bots:
  enabled: true
  providers:
    - google
    - bing
    - openai

database:
  maxmind_edition: GeoLite2-Country-CSV
  secrets_file: ~/.secrets
```

Validation rules:

- `version` must be present.
- `targets` entries must be normalized to uppercase country codes.
- `whitelist` entries must parse as IP addresses or CIDR networks.
- `blacklist` entries must parse as IP addresses or CIDR networks.
- invalid entries should fail with a clear error message that includes
  the section and value.

When `banip.yaml` exists, `banip build` should prefer it over the
legacy flat files. When it does not exist, preserve current behavior.

### Migration

Add a migration path through `banip database init` or a dedicated future
subcommand.

Migration should:

- read existing `targets.txt`, `custom_whitelist.txt`, and
  `custom_blacklist.txt`,
- convert them into the YAML structure,
- preserve comments where practical,
- not delete the original files,
- refuse to overwrite an existing `banip.yaml` unless an explicit
  overwrite flag is provided.

In YAML mode, if `banip build` prunes redundant custom blacklist entries,
it should update the YAML blacklist section rather than rewriting
`custom_blacklist.txt`.

## Build Refactor

Before adding bot and YAML behavior, refactor `banip build` so the main
task runner remains an orchestration layer instead of one long
procedure. This should be behavior-preserving.

Keep current file formats, output ordering, status labels, and build side
effects unchanged except where bot or YAML support explicitly requires a
change.

Move stable build steps into helpers for:

- setup and required-file validation,
- source config loading,
- custom blacklist loading and pruning,
- target country loading and GeoLite filtering,
- custom whitelist loading,
- ipsum pruning and compaction,
- redundant custom entry pruning,
- rendered blacklist and whitelist writing,
- final stats table creation.

Keep the refactor modest and local to the build workflow. Do not
introduce a broad package reorganization.

## Robots.txt And IP Blocking

`robots.txt` and IP blocking solve different problems.

Use `robots.txt` as the preferred signal for compliant crawlers. IP
blocking is stronger enforcement at the network layer, but it can also
block useful indexing, previews, search features, ad validation, and
user-triggered fetches.

Future documentation should explain that blocking crawler IP ranges is a
deliberate policy choice, not a drop-in replacement for `robots.txt`.

## Verification

Future implementation should include tests for:

- parser registration for `bots` and `database`,
- each bot provider adapter,
- malformed provider JSON,
- missing fields and non-CIDR values,
- duplicated ranges,
- IPv4 and IPv6 ranges,
- empty provider results,
- refreshing one provider while preserving other providers,
- `banip bots refresh all`,
- `banip bots list`,
- `banip bots check IP`,
- unchanged build output when `botdata.json` is missing,
- missing, empty, and invalid `botdata.json`,
- build-time in-memory merging of custom and managed ranges,
- `--no-bots` skipping stored bot ranges,
- no bot-range writes to custom blacklist data,
- ipsum download success and HTTP failures,
- MaxMind credential loading from environment variables,
- MaxMind credential loading from `~/.secrets`,
- MaxMind `HEAD` metadata handling,
- MaxMind zip download and extraction,
- invalid MaxMind zip files,
- missing required GeoLite CSV files,
- atomic geolite replacement only after validation,
- YAML config loading and validation,
- flat-file fallback when `banip.yaml` is absent,
- migration from existing flat files into YAML,
- unchanged rendered blacklist and whitelist contents before YAML and
  bot ranges are enabled,
- existing status output and final stats still appearing.

Run these checks after implementation:

- `just lint`,
- `just typecheck`,
- `just test`.

## Assumptions

- This is a future-work plan, not an implementation.
- Python compatibility remains `>=3.12`.
- Existing flat-file installs remain supported for at least one release.
- `~/.secrets` uses dotenv-style key-value syntax, not shell code.
- MaxMind credentials are required only for GeoLite downloads.
- `banip bots` refreshes managed bot state.
- `banip build` consumes managed bot state.
- Missing `botdata.json` is ignored unless a bot refresh is requested.
- Provider feeds may differ in format and may require provider-specific
  adapters.
- YAML is preferred over TOML because user-edited metadata is expected
  to evolve.
