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
to look up one address. Refresh and list output includes provider range
counts and locally formatted refresh times. Check output identifies
each provider network containing the queried address, or reports that
no managed range contains it.

When bot data exists and `bots.enabled` is true, `banip build` adds
those networks in a separate managed section of the rendered
blocklist.
