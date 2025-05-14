# `reneelutil`

This package provides a few scripts intendended to be run from the commandline (`format_edgelist.py` and `run_reneel.py`) as well as a library of functions for working with the output of those files (`data.py`)

## `run_reneel.py`

The basic usage options are
```shell
run_reneel.py edgelist_file [options]
run_reneel.py @options_file [options]
run_reneel.py --config configuration_file [options]
```

### Options

A full list of options can be viewed using the `-h` option.
Because there are so many commandline options, it can become unwieldy to write out the command, and difficult to make minor modifications when you want to run it again. To make life easier, there are two ways of reading options from a file.

#### Options via plain text
Option one more or less directly passes the contents of a text file to the argument parser (see [argparse documentation](https://docs.python.org/3/library/argparse.html#fromfile-prefix-chars))

```shell
run_reneel.py edgelist_file -x some/path/a.out -c 0.1 0.2 -g 3 -s 12345
```

is equivalent to
```shell
run_reneel.py @options
```
where `options` is a text file with contents
```
edgelist_file
-x some/path/a.out
-c 0.1 0.2
-g 3       # a comment explaining what this parameter does
-s 12345
```
Comments are optional and ignored by the argument parser (implemented via [custom arg line parser](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.convert_arg_line_to_args))

#### Options via toml file
You can also pass some or all arguments via a [`.toml` file](https://toml.io/en/). The toml file should contain a table called `run_reneel` with commandline arguments as key-value pairs (using the long form of the commandline option). A sample file is provided in the root directory of this repository; a short example is provided below. Note that the verbosity level (`-v` or `--verbose`) cannot be set via `toml` file.


> ```shell
> run_reneel.py edgelist_file -x some/path/a.out -c 0.1 0.2 -g 3 -s 12345
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
> seed = [12345]
> ```
> The main "gotcha" here is that `file`, `chi`, and `seed` must be [arrays](https://toml.io/en/v1.0.0#array), even if there's only one value.