# reneel-utils: Docker Workflow

## Overview

The `reneel-utils` repo provides Python scripts for preprocessing edgelists and running
the [generalized-modularity-density](https://github.com/prameshsingh/generalized-modularity-density)
community detection algorithm. A Docker image bundles the compiled C binary and the Python
scripts so the workflow runs on any machine with Docker installed.

## Setup

### 1. Build the Docker image

From the `reneel-utils` directory:

```bash
make build
```

This clones and compiles the C code inside Docker (using gcc-9 + OpenMP) and copies
the Python scripts into the image. You only need to rebuild when you update the scripts
(`make build` again) or want to pick up upstream C changes (`docker build --no-cache`).

### 2. Set up a project directory

Each analysis project lives in its own directory. The recommended structure:

```
brain-networks/
├── Makefile            # delegates to reneel-utils
├── data/
│   ├── network-1/
│   │   ├── config.mk
│   │   ├── network-1.txt
│   │   └── run.toml
│   └── network-2/
│       ├── config.mk
│       ├── network-2.txt
│       └── run.toml
```

### 3. Create the project Makefile

Put this `Makefile` in your project root (edit the `RENEEL_UTILS` path):

```makefile
RENEEL_UTILS = /path/to/reneel-utils

PROJ ?= data/network-1   # default project; override with PROJ=data/network-2

-include $(PROJ)/config.mk

%:
	$(MAKE) -C $(RENEEL_UTILS) $@ \
	    DATA_DIR=$(DATA_DIR) \
	    OUTPUT_DIR=$(OUTPUT_DIR) \
	    CONFIG=$(CONFIG)
```

The `PROJ ?=` line sets a default so that bare `make format` works without specifying
a project every time. Override it on the command line to switch projects.

### 4. Create a `config.mk` for each dataset

Each subdirectory gets a `config.mk` with its own paths and filenames:

```makefile
# data/network-1/config.mk
DATA_DIR   = /absolute/path/to/brain-networks/data/network-1
OUTPUT_DIR = /absolute/path/to/brain-networks/data/network-1/results
CONFIG     = run.toml
```

`CONFIG` is the TOML file passed to both the format and run step, resolved relative to `DATA_DIR` inside the container. The config file is the only way to pass arguments to either formatter or runner; the suggestion is to write one like the example in [/data/karate.toml](/data/karate.toml). In fact, you can save a bit of work by always naming the file `reneel.toml`; then your `config.mk` only needs to specify the `DATA_DIR` and `OUTPUT_DIR`.

---

## Running the workflow

### Preprocess an edgelist

```bash
make format PROJ=data/network-1
```

Produces `clean_*`, `degree_*`, `info_*`, and `key_*` files in `DATA_DIR`.

### Run the algorithm

```bash
make run PROJ=data/network-1
```

Results are written to `OUTPUT_DIR`. The `CONFIG` TOML file controls chi values,
number of runs, ensemble sizes, etc.

### Run both steps in sequence

```bash
make all PROJ=data/network-1
```

### Use the default project

If `PROJ` is set in the Makefile (e.g. `PROJ ?= data/network-1`), you can omit it:

```bash
make format
make run
```

### Open a debug shell

```bash
make shell PROJ=data/network-1
```

Drops you into a bash shell inside the container with `DATA_DIR` mounted at `/data`.
The compiled binary is at `/app/reneel` and the scripts are at `/app/reneelutil/`.

---

## TOML config format

The `run.toml` file controls how `format_edgelist.py` and `run_reneel.py` operate.
Do **not** set `reneelpath` in this file — the Makefile handles it automatically.

```toml
[format_edgelist]
file = ["network-1.csv"]
sep = "comma"

[run_reneel]
file = ["network-1.csv"]   
chi = [0.0, 0.5, 1.0]
nruns = 5
rg_ensemble_size = 20
reneel_ensemble_size = 16
```

The `file` key uses a list so you can run multiple networks in one invocation.
Paths are relative to `DATA_DIR`.
