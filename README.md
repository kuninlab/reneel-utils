# reneel_utils

Workflow for network analysis using reneel.

## Usage

Assuming your directory structure looks like this:
```
|-- generalized-modularity-density
|    -- reneelexecutable
|-- reneel-utils
|-- YOUR_PROJECT
|   |-- data
|        -- edgelist_file.csv
|   |-- results
```

You navigate to `YOUR_PROJECT` and run
```shell
format_edgelist data/edgelist_file.csv
run_reneel data/edgelist_file.csv -r -x ../generalized-modularity-density/reneelexecutable -o results/
```

Note that `format_edgelist` has lots of options; use `-h` to find out more. Note that the `-x` option specifies the location of the actual reneel executable; by default `run_reneel` will look for `a.out` in the current working directory.

## Set up

### Easy set up

Download this repo somewhere convenient, then add the `src` directory to your path:

```shell
git clone 
```


Download the [generalized modularity density](https://github.com/prameshsingh/generalized-modularity-density) repo and compile the executable

```shell
git clone git@github.com:prameshsingh/generalized-modularity-density.git
cd generalized-modularity-density
gcc-9 main.c help.c rg.c -fopenmp -lm
mv a.out reneel  # not required, just convenient
cd ..
```