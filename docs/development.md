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

Run the complete local quality suite with:

```console
just check
```

This runs formatting and lint checks, static type checks, tests, the
strict documentation build, and the direct-dependency license policy.
The individual recipes remain available when a focused check is more
appropriate:

```console
just lint
just typecheck
just test
just docs-build
just licenses
```

Run `just docs-serve` to preview documentation locally. The generated
`site/` directory is not tracked. GitHub Pages builds the same strict
site after documentation changes reach `main`.

## Changelog and releases

Pull-request titles use Conventional Commits because squash merges make
the title the commit subject on `main`. CI validates the title. The
supported user-facing types are:

| Type | Changelog section |
| --- | --- |
| `feat` | Added |
| `change` | Changed |
| `deprecate` | Deprecated |
| `remove` | Removed |
| `fix` | Fixed |
| `security` or `fix(security)` | Security |
| `perf` | Performance |
| `deploy` | Deployment & Operations |
| `docs` | Documentation |
| `build(deps)` or `build(deps-dev)` | Dependencies |
| `revert` | Reverted |

Use an optional scope when it adds useful context, for example
`fix(config): reject an invalid country` or
`deploy(release): validate package artifacts`. Mark a breaking change
with `!`, as in `change!: rename a configuration key`, and explain the
migration in the commit body's `BREAKING CHANGE:` footer. Routine
`build`, `chore`, `ci`, `refactor`, `style`, and `test` commits do not
appear in the changelog unless they are breaking.

Preview changelog-visible commits since the latest release without
changing files:

```console
just changelog
```

Prepare a release from a clean release-preparation branch with an
explicit canonical PEP 440 version:

```console
just bump 2.1.1
just check
git add CHANGELOG.md changelogs pyproject.toml uv.lock
git commit -m "chore(release): prepare for 2.1.1"
```

The bump command updates synchronized project versions and the lockfile,
generates the release section, and restores the original files if any
step fails. It is safe to rerun the same untagged version after adding
release changes. Patch and prerelease entries remain in the active
`X.Y` line; starting a new minor or major line moves older entries to
[the changelog archive](https://github.com/geozeke/banip/tree/main/changelogs).

After the release-preparation change is merged, update local `main` and
create the release tag:

```console
git switch main
git pull --ff-only origin main
just tag-release
```

Tagging requires a clean `main` that exactly matches `origin/main`,
synchronized metadata, committed release notes, and a tag that does not
already exist. It creates and pushes one annotated `vX.Y.Z` tag. The tag
workflow validates the release candidate, builds and smoke-tests the
wheel and source distribution, publishes the distributions to a package
index, and then publishes the GitHub Release.

Prerelease tags such as `v2.1.1rc1` publish to TestPyPI and create a
GitHub prerelease. Stable tags such as `v2.1.1` publish automatically to
PyPI and create a stable GitHub Release. The GitHub release is not
created if the corresponding package-index publication fails.

Stable releases move the mutable `latest` Git tag only after PyPI and
GitHub publication succeed. The workflow never moves `latest` for a
failed release or a prerelease.

Do not attach a GitHub Release to `latest` or configure it as an
immutable or protected tag. The release workflow requires permission to
force-update this one mutable installation ref.

Promote a prerelease by preparing and tagging the matching stable
version, such as `2.1.1`. If the promotion has no additional
changelog-visible commits, the release notes record the promotion from
the prerelease.

### Trusted publishing setup

The release workflow uses PyPI Trusted Publishing and does not use
long-lived API tokens. Before the first publication:

1. Create GitHub environments named `testpypi` and `pypi`. Do not add a
   deployment approval rule when releases should remain fully
   automatic.
2. Register a pending publisher for the `banip` project on TestPyPI and
   PyPI. Use owner `geozeke`, repository `banip`, workflow
   `release.yml`, and the matching GitHub environment name.
3. Allow GitHub Actions read and write workflow permissions so the
   stable release job can update the `latest` tag.

Recheck that the project name is available immediately before
registering the pending PyPI publisher. The first successful trusted
publication claims a pending project.

## Dependency updates and security

Dependabot checks direct uv and GitHub Actions dependencies weekly.
Minor and patch uv updates are grouped into one pull request, while
major uv updates and GitHub Actions updates remain individual.
Dependabot automatically rebases open pull requests when its scheduled
check runs or the target branch changes.

Eligible minor and patch updates receive squash auto-merge only after
the required `Quality` and `Dependabot security gate` checks succeed.
Major updates, updates without recognized semantic-version metadata,
and pull requests with maintainer changes require manual review and
merging.

The security workflow runs independent repository scanning, Python
dependency auditing, direct-dependency license validation, and CodeQL
analysis for Dependabot pull requests, relevant pushes to `main`, its
weekly schedule, and manual runs. Each job writes a summary table while
the corresponding step log contains full details. The workflow creates
no issue, dependency commit, or remediation pull request.

Repository administrators should enable the dependency graph and
Dependabot Alerts in the repository's security settings. Leave
automatic Dependabot security updates disabled when remediation pull
requests should remain maintainer-controlled. For scheduled workflow
failure email, enable Actions email notifications and select the option
to notify only for failed workflows.

When an audit finds a vulnerable transitive dependency, prepare one
`fix(security):` pull request for compatible findings from that audit
cycle. Use the resolver rather than editing `uv.lock` by hand:

```console
uv lock --upgrade-package <package>
```

If the parent dependency excludes every fixed version, update or
replace the parent instead of forcing an incompatible transitive
version. Document any temporary risk acceptance or mitigation in the
security pull request.

GitHub branch protection for `main` must require branches to be up to
date and require the `Quality` and `Dependabot security gate` checks.
Repository administrators must also enable squash merging and
auto-merge and allow GitHub Actions read and write workflow permissions.
