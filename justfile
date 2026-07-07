set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
project_name := "banip"

# Show help
default: help

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
    uv run python scripts/bump.py {{version}}
    just sync

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

# Format Python files and apply fixable Ruff lint rules
format:
    uv run ruff check --fix .
    uv run ruff format .

# --------------------------------------------

# Show available recipes
help:
    @just --list

# --------------------------------------------

# Run lint checks
lint:
    uv run ruff check .
    uv run ruff format --check .

# --------------------------------------------

# Show outdated top-level dependencies
outdated:
    #!/usr/bin/env bash
    uv tree --outdated --depth=1 --all-groups | awk '
        /latest/ {
            found = 1
            print
        }
        END {
            if (!found) {
                print "No outdated top-level dependencies found."
            }
        }
    '

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

# Generate release tag
tag-release:
    bash ./scripts/release_tags.sh

# --------------------------------------------

# Generate release tag and update latest
tag-release-latest:
    bash ./scripts/release_tags.sh --latest

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
    uv run mypy src

# --------------------------------------------

# Upgrade runtime and development dependencies
upgrade: _require_setup
    uv sync --upgrade --all-groups
