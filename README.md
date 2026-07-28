# banip

<img
  src="assets/banip-logo.png"
  alt="banip logo"
  width="120"
/>

banip creates country-focused IP blocklists from MaxMind GeoLite2 data,
the ipsum threat-intelligence feed, and optional plugin commands.

## Documentation

Read the full documentation at <https://geozeke.github.io/banip/>.

It covers installation, configuration, commands, managed bot ranges,
plugins, development, and the country-code reference.

## Quick start

```console
uv tool install --managed-python --from git+https://github.com/geozeke/banip.git@latest banip
banip database init
banip database update
banip build
```

`banip database update geolite` requires MaxMind credentials. See the
[getting-started guide](https://geozeke.github.io/banip/getting-started/)
for the required account and configuration details.

## Development

```console
just setup
just lint
just typecheck
just test
just docs-build
```

## License

banip is released under the MIT license. See [LICENSE](LICENSE).
