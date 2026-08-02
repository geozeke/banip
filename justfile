set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
project_name := "banip"

# Show available recipes
default:
    @just --list

# --------------------------------------------

# Open a generated HTML report in the default browser
_display_webpage web_path:
    #!/usr/bin/env python3
    import webbrowser
    from pathlib import Path
    p = Path(".").resolve() / "{{web_path}}"
    if not p.exists():
        raise SystemExit(f"File not found: {p}")
    url = f"file://{p}"
    print(f"Coverage report: {url}")
    webbrowser.open(url, new=2)

# --------------------------------------------

# Require initial setup to be complete
_require_setup:
    #!/usr/bin/env bash
    if [ ! -f .init/setup ]; then
        echo 'Please run "just setup" first'
        exit 1
    fi

# --------------------------------------------

# Bump the project version and generate changelog
bump version:
    uv run python -m scripts.bump_version {{version}}

# --------------------------------------------

# Preview user-facing changes since the latest release
changelog:
    #!/usr/bin/env bash
    if ! command -v git-cliff >/dev/null 2>&1; then
        echo "banip requires git-cliff. See docs/development.md." >&2
        exit 1
    fi
    git-cliff --unreleased

# --------------------------------------------

# Clean python runtime and build artifacts
clean:
    echo "Cleaning python runtime and build artifacts"
    rm -rf build dist .*cache htmlcov .release-notes.md
    rm -rf .tox .nox .hypothesis .pybuilder .pytype .pyre
    rm -rf develop-eggs downloads eggs parts sdist var wheels
    find . -type d -name __pycache__ -exec rm -rf {} \; -prune
    find . -type d -name .ipynb_checkpoints -exec rm -rf {} \; -prune
    find . -type d -name .pytest_cache -exec rm -rf {} \; -prune
    find . -type d -name .eggs -exec rm -rf {} \; -prune
    find . -type d -name '*.egg-info' -exec rm -rf {} \; -prune
    find . -type f -name .DS_Store -delete
    find . -type f -name '._*' -delete
    find . -type f -name '*.egg' -delete
    find . -type f -name '*.pyc' -delete
    find . -type f -name '*.pyo' -delete

# --------------------------------------------

# Serve the Zensical documentation site locally
docs-serve:
    uv run --group docs zensical serve

# --------------------------------------------

# Build the Zensical documentation site in strict mode
docs-build:
    uv run --group docs zensical build --clean --strict

# --------------------------------------------

# Format Python files and apply fixable Ruff lint rules
format:
    uv run ruff check --fix .
    uv run ruff format .

# --------------------------------------------

# Run lint checks
lint:
    uv run ruff check .
    uv run ruff format --check .

# --------------------------------------------

# Validate direct dependency licenses against project policy
licenses:
    uv run python scripts/check_dependency_licenses.py

# --------------------------------------------

# Reset the project state
reset: clean
    echo "Resetting project state"
    rm -rf .init .venv

# --------------------------------------------

# Initialize the project environment with runtime and development dependencies
setup:
    #!/usr/bin/env bash
    if [ ! -f .init/setup ]; then
        if ! command -v uv >/dev/null 2>&1; then
            echo "{{project_name}} requires uv. See README for instructions."
            exit 1
        fi
        if ! command -v git >/dev/null 2>&1; then
            echo "{{project_name}} requires git. See README for instructions."
            exit 1
        fi
        if ! command -v git-cliff >/dev/null 2>&1; then
            echo "{{project_name}} requires git-cliff. See README for instructions."
            exit 1
        fi
        mkdir -p scratch .init
        touch .init/setup
        uv sync --frozen --all-groups
    else
        echo "Initial setup is already complete. If you are having issues, run:"
        echo
        echo "just reset"
        echo "just setup"
        echo
    fi

# --------------------------------------------

# Sync runtime and development dependencies with the lockfile
sync: _require_setup
    uv sync --all-groups

# --------------------------------------------

# Run the complete local quality-check suite
check: lint typecheck test docs-build licenses

# --------------------------------------------

# Generate and push the release tag
tag-release:
    uv run python -m scripts.tag_release

# --------------------------------------------

# Run pytest with --tb=short option
test:
    uv run pytest --tb=short

# --------------------------------------------

# Run tests with coverage reporting
coverage:
    uv run pytest --tb=short --cov=src --cov-report=term-missing --cov-report=html

# --------------------------------------------

# Run coverage and open HTML report in browser
coverage-open: coverage
    just _display_webpage "htmlcov/index.html"

# --------------------------------------------

# Run static type checks
typecheck:
    uv run mypy src scripts
