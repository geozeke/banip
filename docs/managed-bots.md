# Managed bot ranges

banip stores crawler and bot provider ranges separately from the manual
denylist. Refresh an individual provider with:

```console
banip bots refresh google
```

Supported providers are `google`, `bing`, `openai`, `anthropic`, and
`meta`. Refresh every provider with:

```console
banip bots refresh all
```

Use `banip bots list` to inspect stored data or `banip bots check <IP>`
to look up one address. When bot data exists and `bots.enabled` is true,
`banip build` adds those networks in a separate managed section of the
rendered blocklist.
