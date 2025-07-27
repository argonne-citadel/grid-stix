SHELL := /bin/bash
.SHELLFLAGS := -e -c
FORCE_COLOR := true

# Colors for pretty printing
ESC := $(shell printf '\033')
COLOR_RESET := $(ESC)[0m
COLOR_BOLD := $(ESC)[1m
COLOR_GREEN := $(ESC)[32m
COLOR_RED := $(ESC)[31m
COLOR_YELLOW := $(ESC)[33m

MAMBA_EXE ?= micromamba
MICROMAMBA_DEV := $(MAMBA_EXE) run -n grid-stix

init: environment.yml
	@echo "$(COLOR_BOLD)Creating development environment...$(COLOR_RESET)"
	@$(MAMBA_EXE) create -yf environment.yml
	@echo "$(COLOR_GREEN)Development environment created successfully!$(COLOR_RESET)"

format:
	@echo "Formatting code..."
	@${MAMBA_DEV} black -q . 
	@find . -type f -iname "*.owl" -not -path "./tac-ontology/*" -exec xmllint --format --output {} {} \;
	@echo "$(COLOR_GREEN)Code formatting complete$(COLOR_RESET)"

black:
	@echo "$(COLOR_BOLD)Formatting Python code...$(COLOR_RESET)"
	@${MICROMAMBA_DEV} black -q src/ python/ 
	@echo "$(COLOR_GREEN)Formatting complete!$(COLOR_RESET)"

lint:
	@echo "$(COLOR_BOLD)Running code quality checks...$(COLOR_RESET)"
	@${MICROMAMBA_DEV} black --check --diff -q src/ python/ 
	@echo "$(COLOR_GREEN)Code quality checks passed!$(COLOR_RESET)"

security:
	@echo "Running security checks..."
	@${MAMBA_DEV} bandit -q -ll -ii -r --skip B108 --skip B104 $(SRC_DIR)/
	@echo "$(COLOR_GREEN)Security precheck complete$(COLOR_RESET)"
	@echo "Checking dependencies for security issues..."
	@${MAMBA} pip freeze | ${MAMBA_DEV} safety check --stdin --json 
	@$(MICROMAMBA_BIN) list -n $(ENV_NAME) -q --json | \
		${MAMBA_DEV} jake ddt -t CONDA_JSON \
	@echo "$(COLOR_GREEN)Security postcheck complete$(COLOR_RESET)"

merge:
	@echo "$(COLOR_BOLD)Merging ontologies...$(COLOR_RESET)"
	@~/Downloads/robot/bin/robot merge \
		--catalog catalog.xml \
		--input vocabularies/grid-stix-2.1-vocab.owl \
		--input contexts/grid-stix-2.1-operational-contexts.owl \
		--input contexts/grid-stix-2.1-environmental-contexts.owl \
		--input core/grid-stix-2.1-assets.owl \
		--input core/grid-stix-2.1-components.owl \
		--input core/grid-stix-2.1-relationships.owl \
		--input observables/grid-stix-2.1-events-observables.owl \
		--input threat/grid-stix-2.1-attack-patterns.owl \
		--input policy/grid-stix-2.1-policies.owl \
		--input nuclear/grid-stix-2.1-nuclear-safeguards.owl \
		--input root/grid-stix-2.1-root.owl \
		--output grid-stix-2.1-full.owl
	@echo "$(COLOR_GREEN)Ontologies merged successfully!$(COLOR_RESET)"

check: merge
	@echo "$(COLOR_BOLD)Checking ontology...$(COLOR_RESET)"
	@${MAMBA_EXE} run -n grid-stix python src/ontology_checker.py
	@echo "$(COLOR_GREEN)Ontology check complete$(COLOR_RESET)"

html: merge
	@echo "$(COLOR_BOLD)Generating HTML graph...$(COLOR_RESET)"
	@${MAMBA_EXE} run -n grid-stix python src/owl_to_html.py grid-stix-2.1-full.owl grid-stix.html

generate: merge
	@echo "$(COLOR_BOLD)Generating Python code...$(COLOR_RESET)"
	@rm -Rf python/*
	@${MAMBA_EXE} run -n grid-stix python -m src.generator grid-stix-2.1-full.owl python/ --log-level INFO 

