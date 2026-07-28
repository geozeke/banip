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

## Dependency updates

Dependabot checks direct uv and GitHub Actions dependencies weekly. It
groups minor and patch uv updates into one pull request, while major uv
updates and GitHub Actions updates remain individual. Dependabot uses
automatic rebasing to refresh open pull requests when the target branch
changes or a scheduled update check runs.

Minor and patch updates are eligible for squash auto-merge after the
required `Quality` check succeeds. Major updates, updates without
recognized semantic-version metadata, and pull requests with maintainer
changes require manual review and merging.

Repository administrators must enable squash merging and auto-merge,
allow GitHub Actions read and write workflow permissions, and configure
branch protection for `main` to require branches to be up to date and
the `Quality` check to pass.

## Releases

Use `just bump <version>` to prepare a release and update changelog
metadata. Do not edit `CHANGELOG.md` directly for feature, fix, or
dependency changes. After release preparation is committed, use
`just tag-release` to publish a version tag, or `just tag-release-latest`
to update the mutable `latest` tag too.
