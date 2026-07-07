# banip Agent Notes

`banip` is a Python 3.12 CLI package for creating country-specific IP
blacklists and whitelists from MaxMind GeoLite2 country data, ipsum
blacklist data, and optional user-provided plugin commands.

## Project Layout

- `src/banip/` contains the application package.
- `src/banip/app.py` is the CLI entry point exposed as `banip`.
- `src/banip/parsers/` contains built-in argparse subcommand parsers.
- `samples/` contains sample target, whitelist, blacklist, and plugin
  files.
- `CHANGELOG.md` contains the active minor release line; older minor
  lines are archived under `changelogs/`.
- `pyproject.toml`, `uv.lock`, and `justfile` define package metadata,
  dependencies, and common project tasks.
- `.github/workflows/` contains GitHub Actions for CI and release
  automation.

## Working Constraints

- Do not traverse, modify, or rely on `.venv/`.
- Do not traverse cache or generated-state directories such as
  `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `__pycache__/`, or
  `.cache/` unless the task explicitly requires it.
- Prefer reading `README.md`, `pyproject.toml`, and files under `src/`
  first.
- Use `rg` for searches and `just` or `uv` for common project tasks when
  needed.
- Prefer `pathlib.Path` objects over raw path strings where practical.
- Prefer truthiness checks like `if value:` and `if not value:` over
  explicit empty or `None` comparisons when they are semantically
  equivalent.
- Use strict NumPy-style docstrings for all function, class, and module
  docstrings.
- Use snake case for variable names.
- Run ruff on any Python code changes or additions.
- When reviewing or modifying `.gitignore`, also check whether Git
  global excludes are configured, for example with
  `git config --global core.excludesfile`.
- Wrap Markdown prose to 72 characters when practical, but do not break
  links, code spans, tables, or other formatting that would be harmed by
  wrapping.
- Keep documentation and metadata consistent when making changes,
  including README content, this file, argparse messages, docstrings,
  and code comments.

## Verification

- Use `just setup` to prepare runtime and development dependencies.
- Use `just lint` after Python code changes.
- Use `just typecheck` when behavior or types change.
- Use `just test` when adding or changing behavior.
