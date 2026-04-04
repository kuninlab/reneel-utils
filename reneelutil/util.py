import argparse
import tomllib
from pathlib import Path


class MyArgumentParser(argparse.ArgumentParser):
    """Overrides the `convert_arg_line_to_args` function to make it easier to use.
    In particular, allows for comments starting with '#'"""
    def convert_arg_line_to_args(self, arg_line: str):
        pre_comment = arg_line.split("#", maxsplit=1)[0].strip()
        return pre_comment.strip().split()
    
def parse_toml_args(file, table):
    """If config file is not none, attempt to read the specified table, and return the dict that is found."""
    if file is not None:
        config_path = Path(file)
        with open(config_path, "rb") as config_file:
            config = tomllib.load(config_file)
        return {k.replace("-", "_"): v for k, v in config[table].items()}
    return dict()