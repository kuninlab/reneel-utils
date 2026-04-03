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
cd reneel-utils/reneelutil/
pip install -e .
```

### Basic installation -- commandline only

Download this repo somewhere convenient, then add the `src` directory to your path:

```shell
git clone git@github.com:kuninlab/reneel-utils.git
cd reneel-utils/reneelutil/
export PATH=$PATH:$(pwd)
```

Both `format_edgelist.py` and `run_rneel.py` look for python in `/opt/anaconda3/bin/python`, because I'm a conda junkie. You can edit those to point to whichever python executable you want; they should work on `python >= 3.9` with only the standard libraries.

### Installing Reneel

Download the [generalized modularity density](https://github.com/prameshsingh/generalized-modularity-density) repo and compile the executable

```shell
git clone git@github.com:prameshsingh/generalized-modularity-density.git
cd generalized-modularity-density
gcc-9 main.c help.c rg.c -fopenmp -lm
mv a.out reneel  # not required, just convenient
```
