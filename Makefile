all: help

# --------------------------------------------

.PHONY: setup
setup: ## setup project with runtime dependencies
ifeq (,$(wildcard .init/setup))
	@(which uv > /dev/null 2>&1) || \
	(echo "banip requires uv. See README for instructions."; exit 1)
	mkdir -p scratch .init
	touch .init/setup
	uv sync --frozen --no-dev
else
	@echo "Initial setup is already complete. If you are having issues, run:"
	@echo
	@echo "make reset"
	@echo "make setup"
	@echo
endif

# --------------------------------------------

.PHONY: dev
dev: ## add development dependencies (run make setup first)
ifneq (,$(wildcard .init/setup))
	uv sync --frozen --all-groups
	@touch .init/dev
else
	@echo "Please run \"make setup\" first"
endif

# --------------------------------------------

.PHONY: upgrade
upgrade: ## upgrade project dependencies
ifeq (,$(wildcard .init/dev))
	uv sync --upgrade --no-dev
else
	uv sync --upgrade --all-groups
endif

# --------------------------------------------

.PHONY: sync
sync: ## sync dependencies with the lock file (use --frozen)
ifeq (,$(wildcard .init/setup))
	@echo "Please run \"make setup\" first" ; exit 1
endif

ifneq (,$(wildcard .init/dev))
	uv sync --all-groups --frozen
else
	uv sync --no-dev --frozen
endif

# --------------------------------------------

.PHONY: reset
reset: clean ## remove venv, artifacts, and init directory
	@echo Resetting project state
	rm -rf .init .mypy_cache .ruff_cache .venv

# --------------------------------------------

.PHONY: clean
clean: ## cleanup python runtime artifacts
	@echo Cleaning python runtime artifacts
	@find . -type d -name __pycache__ -exec rm -rf {} \; -prune
	rm -rf dist

# --------------------------------------------

.PHONY: help
help: ## show help
	@echo ""
	@echo "Available Commands"
	@echo "========================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk \
	'BEGIN {FS = ":.*?## "}; \
	{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
