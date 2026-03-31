set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
project_name := "banip"

# Show help
default: help

# --------------------------------------------

# Private handler for commits
_commit latest:
    #!/usr/bin/env bash
    git add .
    git commit -m "Bump version"
    git push origin main
    if [[ "{{latest}}" == "true" ]]; then
        ./run/release_tags.sh --latest
    else
        ./run/release_tags.sh
    fi

# --------------------------------------------

# Initialize the project environment
setup:
    #!/usr/bin/env bash
    if [ ! -f .init/setup ]; then
        if ! command -v uv >/dev/null 2>&1; then
            echo "{{project_name}} requires uv. See README for instructions."
            exit 1
        fi
        mkdir -p scratch .init run
        touch .init/setup
        cp ./scripts/* ./run
        find ./run -name '*.sh' -exec chmod 744 {} \;
        export UV_PYTHON_PREFERENCE=only-managed
        uv sync --frozen --no-dev
    else
        echo "Initial setup is already complete. If you are having issues, run:"
        echo
        echo "just reset"
        echo "just setup"
        echo
    fi

# --------------------------------------------

# Provision development dependencies
dev:
    #!/usr/bin/env bash
    if [ ! -f .init/setup ]; then
        echo 'Please run "just setup" first'
        exit 1
    fi
    export UV_PYTHON_PREFERENCE=only-managed
    uv sync --all-groups --frozen
    touch .init/dev

# --------------------------------------------

# Upgrade dependencies
upgrade:
    #!/usr/bin/env bash
    if [ ! -f .init/setup ]; then
        echo 'Please run "just setup" first'
        exit 1
    fi

    cp -f ./scripts/* ./run
    find ./run -name '*.sh' -exec chmod 744 {} \;

    if [ -f .init/dev ]; then
        uv sync --upgrade --all-groups
    else
        uv sync --upgrade --no-dev
    fi

# --------------------------------------------

# Sync dependencies with the lockfile (frozen)
sync:
    #!/usr/bin/env bash
    if [ ! -f .init/setup ]; then
        echo 'Please run "just setup" first'
        exit 1
    fi

    if [ -f .init/dev ]; then
        uv sync --all-groups
    else
        uv sync --no-dev
    fi

# --------------------------------------------

# Clean python runtime artifacts
clean:
    @echo "Cleaning python runtime artifacts"
    find . -type d -name __pycache__ -exec rm -rf {} \; -prune
    rm -rf dist

# --------------------------------------------

# Reset the project state
reset: clean
    echo "Resetting project state"
    rm -rf .init .mypy_cache .ruff_cache .venv run

# --------------------------------------------

# Bump the project version and generate changelog
bump version:
    uv run run/bump.py {{version}}
    just sync

# --------------------------------------------

# Commit, push, update symantic version, EXCLUDE the "latest" tag
commit:
    just _commit false    

# --------------------------------------------

# Commit, push, update symantic version, INCLUDE the "latest" tag
commit-latest:
    just _commit true

# --------------------------------------------

# Generate release tags
tags:
    ./run/release_tags.sh

# --------------------------------------------

# Rebase to the main branch
rebase:
    ./run/rebaseline.sh

# --------------------------------------------

# Show available recipes
help:
    @just --list
