import argparse
import logging
import tomllib
from pathlib import Path

_IGNORE_IN_MERGE = frozenset({"file", "config"})


# Maps old config/arg key names to their new standard equivalents.
_ALIASES = {
    "file":      "input",
    "outputdir": "output",
}


class MyArgumentParser(argparse.ArgumentParser):
    """Overrides the `convert_arg_line_to_args` function to make it easier to use.
    In particular, allows for comments starting with '#'"""
    def convert_arg_line_to_args(self, arg_line: str):
        pre_comment = arg_line.split("#", maxsplit=1)[0].strip()
        return pre_comment.strip().split()


def parse_toml_args(file, table):
    """
    If config file is not None, read the specified table and return it as a dict.

    Deprecated key names (``file``, ``outputdir``) are transparently mapped to
    their standard equivalents (``input``, ``output``) if the new names are not
    already present, and a deprecation warning is logged.
    """
    if file is None:
        return dict()
    config_path = Path(file)
    with open(config_path, "rb") as config_file:
        config = tomllib.load(config_file)
    result = {k.replace("-", "_"): v for k, v in config.get(table, {}).items()}
    for old, new in _ALIASES.items():
        if old in result and new not in result:
            logging.warning(
                f"Config key '{old}' is deprecated in [{table}]; use '{new}' instead."
            )
            result[new] = result.pop(old)
    return result


def merge_args(cli_args, cfg, defaults):
    """Merge parsed CLI args, TOML config, and hardcoded defaults.

    Priority (highest to lowest):
      1. Explicit CLI args (non-None values, excluding 'file' and 'config')
      2. TOML config values
      3. defaults dict

    Args that were not passed on the CLI are None (requires all argparse defaults
    to be set to None for overridable args) and therefore don't override TOML.
    """
    explicit_cli = {k: v for k, v in vars(cli_args).items()
                    if v is not None and k not in _IGNORE_IN_MERGE}
    cfg.update(explicit_cli)
    for k, v in defaults.items():
        cfg.setdefault(k, v)
    return cfg


def remap_paths_for_docker(args, output_dir):
    """Remap input file paths for Docker execution.

    Strips directory portions of input paths and prepends /data/, so that
    a file like 'path/to/network.txt' becomes '/data/network.txt'.
    Sets output to output_dir if not already set.
    """
    if args.get("input"):
        args["input"] = [f"/data/{Path(f).name}" for f in args["input"]]
    if not args.get("output"):
        args["output"] = output_dir
