all: help

# --------------------------------------------

.PHONY: setup
setup: ## setup project with runtime dependencies
ifeq (,$(wildcard .init/setup))
	@(which uv > /dev/null 2>&1) || \
	(echo "banip requires uv. See README for instructions."; exit 1)
	@if [ ! -d "./scratch" ]; then \
		mkdir -p scratch; \
	fi
	@if [ ! -d "./data" ]; then \
		mkdir -p data/geolite; \
	fi
	@if [ ! -d "./src/plugins/parsers" ]; then \
		mkdir -p src/plugins/parsers; \
		touch src/plugins/parsers/__init__.py; \
	fi
	@if [ ! -d "./src/plugins/code" ]; then \
		mkdir -p src/plugins/code; \
		touch src/plugins/code/__init__.py; \
	fi
	mkdir .init
	touch .init/setup
	uv sync --no-dev
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
	uv sync
	@touch .init/dev
else
	@echo "Please run \"make setup\" first"
endif

# --------------------------------------------

.PHONY: upgrade
upgrade: ## upgrade banip code and dependencies
	@echo Upgrading banip
	git pull
	@echo Upgrading dependencies
ifeq (,$(wildcard .init/dev))
	uv sync --no-dev --upgrade
else
	uv sync --upgrade
endif

# --------------------------------------------

.PHONY: reset
reset: clean ## remove venv, artifacts, and init directory
	@echo Resetting project state
	rm -rf .init .mypy_cache .ruff_cache .venv dist

# --------------------------------------------

.PHONY: clean
clean: ## cleanup python runtime artifacts
	@echo Cleaning python runtime artifacts
	@find . -type d -name __pycache__ -exec rm -rf {} \; -prune

# --------------------------------------------

.PHONY: help
help: ## show help
	@echo Please specify a target. Choices are:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk \
	'BEGIN {FS = ":.*?## "}; \
	{printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'