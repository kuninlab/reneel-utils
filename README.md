# reneel-utils

Workflow for network analysis using reneel, as well as utilities for managing the output.

## Usage -- clustering network data

Assuming your directory structure looks like this:
```
YOUR_PROJECT
|-- generalized-modularity-density/
|    -- reneelexecutable
|-- reneel-utils/
|-- YOUR_PROJECT/
|   |-- data/
|   |    -- edgelist_file.csv
|   |-- results/
```

You navigate to `YOUR_PROJECT` and run
```shell
format_edgelist data/edgelist_file.csv --sep comma
run_reneel data/edgelist_file.csv -r -x ../generalized-modularity-density/reneelexecutable -o results/clustering/
```

Note that `format_edgelist` has lots of options; use `-h` to find out more.
Likewise, `run_reneel` has lots of options (see the [README](reneelutile/README.md) for help configuring `run_reneel`).
The `-x` option specifies the location of the actual reneel executable; by default `run_reneel` will look for `a.out` in the current working directory.

If the above commands don't work after setup (e.g. because `python` is not in `/opt/anaconda3/bin/`), you can also run this as 
```shell
python format_edgelist data/edgelist_file.csv
python run_reneel data/edgelist_file.csv -r -x ../generalized-modularity-density/reneelexecutable -o results/clustering/
```

## Using Docker

If you can't get [reneel](https://github.com/prameshsingh/generalized-modularity-density) to compile on your computer, you can use Docker to build and run everything. The workflow would be like this:

```shell
cd /path/to/reneel-utils
make build                                        # takes a few minutes first time
make format INPUT=edgelist DATA_DIR=/path/to/data
make run CONFIG=run.toml DATA_DIR=/path/to/data
```
In this case, you should specify the reneel-run parameters in a toml file, as explained in [reneelutil/README.md](reneelutil/README.md#Options-via-toml-file), except you do **not** specify the location of the reneel executable (do not pass `-x` or `--reneelpath` options)

## Using Snakemake

`workflow/reneel.smk` is a Snakemake module that downloads and compiles reneel, formats edgelists, and runs reneel once per (network, chi, seed). Compilers, OpenMP, and this package all come from a conda env, so nothing needs to be installed by hand. In your project's Snakefile:

```python
module reneel:
    snakefile: github("kuninlab/reneel-utils", path="workflow/reneel.smk", tag="<release tag>")
    config: config["reneel"]
use rule * from reneel

rule all:
    input: rules.reneel_all.input
```

and in `config.yaml`:

```yaml
reneel:
  networks:                      # values for the {dataset} and {networkname} wildcards
    - {dataset: fafb, networkname: mbnetwork}
  chi_replicates:                # number of seeds per chi value
    - {chi: 0.0, n_replicates: 100}
    - {chi: 0.1, n_replicates: 10}
  seed_multiplier: 1998597987    # seeds are seed_multiplier * i
  krg: 2
  rg_ensemble_size: 10
  reneel_ensemble_size: 10
  threads: 10
  format_args: "--sep comma --skip 1"   # passed to format_edgelist
  # optional, shown with defaults:
  # network_dir: "data/processed/{dataset}"   # where {networkname}{ext} lives
  # results_dir: "results/reneel/{dataset}"
  # ext: ".csv"
  # executable: "resources/reneel/reneel"
  # commit: <pinned commit of sekunder/generalized-modularity-density>
```

Run with `snakemake --sdm conda` (`--use-conda` on Snakemake < 8). On a cluster, compute nodes often have no internet access, so create the env and build reneel on the login node first:

```shell
snakemake --sdm conda --conda-create-envs-only
snakemake --sdm conda -c1 resources/reneel/reneel
```

(`reneel_build` is a local rule, so it never gets submitted to a compute node anyway.)

Outputs are `results/reneel/{dataset}/partition_{networkname}_{seed}-{chi}{ext}` (and `results_...`), which `get_available_clustering` and `load_partition` understand.

## Usage -- loading clustering output

The output of `run_reneel` uses specific file name formats to allow for easily organizing data.
Supposing you have done everything as in the section above, then the python code below will produce a `pandas` dataframe listing available clustering info.

```python
from reneelutil.data import get_available_clustering, load_selected_runs
get_available_clustering(clustering_dir="../results/clustering")
```

## Set up

### Package installation

#### pip installing from github
You can install this repository as a python package straight from github using `pip`. If you just need the utility functions in `data.py` (i.e. for finding results files from previous runs of reneel, loading the partition data, etc.) then you can probably get away with

```shell
pip install "git+https://github.com/kuninlab/reneel-utils.git"
```

#### pip installing locally 
If you also need to use the commandline scripts or will be editing this package as you go, it might be more convenient to `git clone` this repository. You can then install the repo as a python package:

```shell
git clone git@github.com:kuninlab/reneel-utils.git
cd reneel-utils
pip install -e .
```

Either way, installing provides the `format_edgelist` and `run_reneel` commands. Requires `python >= 3.11`.

### Installing Reneel

The Snakemake module and the Docker image both build reneel for you. To build it by hand, use the [fork with the OpenMP thread-count fix](https://github.com/sekunder/generalized-modularity-density/tree/fix-omp-thread-count):

```shell
git clone --branch fix-omp-thread-count https://github.com/sekunder/generalized-modularity-density.git
cd generalized-modularity-density
gcc main.c help.c rg.c -fopenmp -lm -O2 -o reneel
```

On macOS, see [docs/compiling-mac.md](docs/compiling-mac.md).
