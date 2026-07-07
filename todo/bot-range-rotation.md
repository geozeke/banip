# Bot Range Rotation

This TODO scopes promoting the private `rotate` plugin to a first-class
`banip` feature. The goal is to manage bot and crawler IP ranges from
multiple providers without storing managed ranges in
`custom_blacklist.txt`.

## Summary

Add a future built-in `banip rotate` command that refreshes provider
range data into a human-readable `~/.banip/botdata.json` file. During
`banip build`, the stored bot ranges should be loaded into an interim
in-memory collection and merged into the final rendered blacklist.

Do not create a separate staged `bot_blacklist.txt` file. The only
persistent managed bot state should be `botdata.json`.

## Command Design

Planned user interface:

- `banip rotate PROVIDER` refreshes one provider.
- `banip rotate --all` refreshes every configured provider.

Rotating one provider must replace only that provider's managed ranges.
It must not remove ranges for other providers already stored in
`botdata.json`.

Initial provider candidates:

- Google crawlers and fetchers.
- Bingbot.
- OpenAI crawlers, such as GPTBot, OAI-SearchBot, and ChatGPT-User.
- Meta crawlers, pending source-format research.

Provider names should be stable lowercase command values. Aliases can be
added later, but the first implementation should keep names explicit and
documented.

## Storage Design

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

Avoid pickle for first-class state. The existing plugin's `botdata.bin`
solves stale-entry cleanup, but it is opaque, difficult to review, and
awkward to migrate.

## Build Integration

Keep `custom_blacklist.txt` user-owned. Do not write bot ranges into it.

During `banip build`:

- Load `botdata.json` if it exists.
- Treat a missing file as no managed bot ranges.
- Parse all stored CIDR ranges into `ipaddress` network objects.
- Merge the parsed bot ranges with other blacklist sources in memory.
- Include those ranges in the final rendered blacklist.
- Leave `custom_blacklist.txt` unchanged except for the existing custom
  pruning behavior.

The final rendered blacklist should include bot ranges, but the managed
bot ranges should remain logically separate from manual custom entries.
If comment sections are added to the rendered blacklist, they should
make this separation visible.

## Provider Adapters

Do not assume every provider publishes clean JSON in the same shape.
Use provider-specific adapters.

Adapter categories:

- JSON `prefixes` adapter for Google, Bing, and OpenAI-style feeds.
- Converted-source adapter for text, HTML, CSV, copied snippets, or
  other irregular provider formats.
- Local-file adapter for manually converted provider data.

Each adapter should normalize provider data into the same internal form:
a provider key, source metadata, and a deduplicated set of CIDR strings.

Meta should be treated as an explicit research item because its bot
ranges may require conversion before `banip` can consume them.

## Robots.txt And IP Blocking

`robots.txt` and IP blocking solve different problems.

Use `robots.txt` as the preferred signal for compliant crawlers. IP
blocking is stronger enforcement at the network layer, but it can also
block useful indexing, previews, search features, ad validation, and
user-triggered fetches.

Future documentation should explain that blocking crawler IP ranges is a
deliberate policy choice, not a drop-in replacement for `robots.txt`.

Reference material for future implementation:

- Google crawler/IP range docs:
  https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests
- Bing published ranges:
  https://www.bing.com/toolbox/bingbot.json
- OpenAI crawler docs:
  https://platform.openai.com/docs/bots

## Migration Notes

If `~/.banip/botdata.bin` exists, a future implementation may offer a
one-time migration to `botdata.json`.

Migration should:

- read the old pickle defensively,
- copy each known provider's ranges into the JSON structure,
- preserve the old file unless the user explicitly removes it,
- fail with a clear message if the pickle cannot be read.

Do not require migration for normal operation. A fresh installation
should only use `botdata.json`.

## Verification

Future implementation should include tests for:

- each provider adapter,
- malformed JSON and irregular converted sources,
- missing fields and non-CIDR values,
- duplicated ranges,
- IPv4 and IPv6 ranges,
- empty provider results,
- rotating one provider while preserving other providers,
- `--all` refreshing all configured providers,
- missing, empty, and invalid `botdata.json`,
- build-time in-memory merging of custom and managed ranges,
- no bot-range writes to `custom_blacklist.txt`.

Run these checks after implementation:

- `just lint`
- `just typecheck`
- `just test`

## Assumptions

- This is a future-work plan, not an implementation.
- The multi-provider UX is `banip rotate PROVIDER` plus
  `banip rotate --all`.
- `botdata.json` is the only persistent managed bot range file.
- Provider feeds may differ in format and may require conversion.
- Python compatibility remains `>=3.12`.
