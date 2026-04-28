IMAGE_NAME    ?= reneel
IMAGE_TAG     ?= latest
DATA_DIR      ?= $(shell pwd)
INPUT         ?=
CONFIG        ?=
OUTPUT_DIR    ?= $(shell pwd)
CONFIG_DIR    ?= $(DATA_DIR)
FORMAT_ARGS   ?=
RUN_ARGS      ?=

BINARY_PATH   := /app/reneel
FORMAT_SCRIPT := /app/reneelutil/format_edgelist.py
RUN_SCRIPT    := /app/reneelutil/run_reneel.py
REPO_DIR      := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

DOCKER_RUN    := docker run --rm \
                   -v "$(DATA_DIR):/data" \
                   -v "$(OUTPUT_DIR):/results" \
                   -v "$(CONFIG_DIR):/configs" \
                   -w /data \
                   $(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: all build format run shell help

all: _check-input _check-config format run

build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) "$(REPO_DIR)"

format: _check-config
	$(DOCKER_RUN) python3 $(FORMAT_SCRIPT) \
	    --config /configs/$(CONFIG) \
	    $(FORMAT_ARGS)

run: _check-config
	$(DOCKER_RUN) python3 $(RUN_SCRIPT) \
	    --config /configs/$(CONFIG) \
	    --reneelpath $(BINARY_PATH) \
	    --outputdir /results \
	    $(RUN_ARGS)

shell:
	docker run --rm -it \
	    -v "$(DATA_DIR):/data" \
	    -w /data \
	    $(IMAGE_NAME):$(IMAGE_TAG) \
	    /bin/bash

_check-input:
	@if [ -z "$(INPUT)" ]; then \
		if [ -z "$(CONFIG)" ]; then \
			echo "Error: INPUT or CONFIG must be set."; \
			echo "Usage: make format INPUT=edgelist.txt"; \
			echo "or:    make format CONFIG=config.toml"; \
	        exit 1; \
		fi \
	fi

_check-config:
	@if [ -z "$(CONFIG)" ]; then \
	    echo "Error: CONFIG is not set. Usage: make run CONFIG=myconfig.toml"; \
	    exit 1; \
	fi

help:
	@echo "Targets:"
	@echo "  build          Build image (clones+compiles C repo, copies scripts)"
	@echo "                   To force re-clone C repo: docker build --no-cache ..."
	@echo "  format         Preprocess edgelist. Requires INPUT=<filename>"
	@echo "                   Optional: FORMAT_ARGS='--sep comma --skip 1'"
	@echo "                   Optional: DATA_DIR=/abs/path/to/data  (default: cwd)"
	@echo "  run            Run reneel via TOML config. Requires CONFIG=<filename>"
	@echo "                   Optional: OUTPUT_DIR=results  (default: results/)"
	@echo "                   Optional: DATA_DIR=/abs/path/to/data  (default: cwd)"
	@echo "                   Note: do not set 'reneelpath' in your TOML config"
	@echo "  all            Run format then run (requires both INPUT and CONFIG)"
	@echo "  shell          Open interactive shell in container (for debugging)"
