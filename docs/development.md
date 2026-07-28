# Development

## Setup

Install Git, Python 3.12, uv, just, git-cliff, and ripgrep. Then run:

```console
just setup
```

Use `just reset` followed by `just setup` to recreate the local runtime
environment. `just clean` removes generated caches and build artifacts
while keeping the environment.

## Quality checks

```console
just lint
just typecheck
just test
just docs-build
```

Run `just docs-serve` to preview documentation locally. The generated
`site/` directory is not tracked. GitHub Pages builds the same strict
site after documentation changes reach `main`.

## Releases

Use `just bump <version>` to prepare a release and update changelog
metadata. Do not edit `CHANGELOG.md` directly for feature, fix, or
dependency changes. After release preparation is committed, use
`just tag-release` to publish a version tag, or `just tag-release-latest`
to update the mutable `latest` tag too.
