import argparse
import logging
import tomllib
from pathlib import Path


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
