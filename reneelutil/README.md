# `reneelutil`

This package provides a few scripts intendended to be run from the commandline (`format_edgelist.py` and `run_reneel.py`) as well as a library of functions for working with the output of those files (`data.py`)

## `run_reneel.py`

The basic usage is
```shell
run_reneel.py edgelist_file [options]
```
or
```shell
run_reneel.py --config configuration_file [options]
```

A full list of options can be viewed using the `-h` option. You can also pass some or all arguments via a [`.toml` file](https://toml.io/en/). The toml file should contain a table called `run_reneel` with commandline arguments as key-value pairs (using the long form of the commandline option). A sample file is provided in the root directory of this repository; a short example is provided below. Note that the verbosity level (`-v` or `--verbose`) can only be set via commandline argument.


> ```shell
> run_reneel.py edgelist_file -x some/path/a.out -c 0.1 0.2 -g 3
> ```
> is equivalent to
> ```shell
> run_reneel.py --config config.toml
> ```
> with the following contents of `config.toml`:
> ```toml
> [run_reneel]
> file = ["edgelist_file"]
> reneelpath = "some/path/a.out"
> chi = [0.1, 0.2]
> rg-parameter = 3
> ```
> The main "gotcha" here is that `file` and `chi` must be [arrays](https://toml.io/en/v1.0.0#array), even if there's only one value.