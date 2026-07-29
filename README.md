# banip

<img
  src="https://raw.githubusercontent.com/geozeke/banip/main/assets/banip-logo.png"
  alt="banip logo"
  width="120"
/>

banip creates country-focused IP blocklists from MaxMind GeoLite2 data,
the ipsum threat-intelligence feed, and user-managed configuration.

## Documentation

Read the full documentation at <https://geozeke.github.io/banip/>.

It covers installation, configuration, commands, managed bot ranges,
development, and the country-code reference.

## Quick start

```console
uv tool install --managed-python banip
banip database init
banip database update
banip build
```

Upgrade an existing installation with `uv tool upgrade banip`.

`banip database update geolite` requires MaxMind credentials. See the
[getting-started guide](https://geozeke.github.io/banip/getting-started/)
for the required account and configuration details.

## Development

```console
just setup
just check
```

See the [development guide](https://geozeke.github.io/banip/development/)
for focused checks, changelog preparation, and release procedures.

## License

banip is released under the MIT license. See [LICENSE](LICENSE).
