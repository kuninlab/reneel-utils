"""Data utilities for loading and working with results from reneel
"""
import argparse, logging, json
from pathlib import Path
import os
import pandas as pd


def load_matrix(matrix_file: Path):
    """Load the given connectivity matrix and return it as a dataframe"""
    logging.info(f"Reading file {matrix_file}")
    return pd.read_csv(matrix_file, index_col=0, header=0)


def matrix_to_edgelist(matrix: pd.DataFrame, pre="rows", threshold=0):
    """Stack the matrix and drop edges at or below threshold"""
    logging.debug(f"Treating {pre} as presynaptic; {threshold = }")
    edgelist = matrix.stack()
    renamer = {0: "weight"}
    if pre == "rows":
        renamer["level_0"] = "bodyId_pre"
        renamer["level_1"] = "bodyId_post"
    else:
        renamer["level_0"] = "bodyId_post"
        renamer["level_1"] = "bodyId_pre"
    edf = pd.DataFrame(edgelist[edgelist > threshold]).reset_index().rename(columns=renamer)
    edf.weight = edf.weight.astype(int)
    return edf


def _get_filename_parts(path):
    """the output files from run_reneel are named 
    [type]_[data name]_[seed]-[chi]-[tmp_id].[ext]
    This splits it at '_' at most twice and returns
    type, data name, seed-chi-tmp_id"""
    return Path(path).stem.split("_", maxsplit=2)


def load_partition(key_file, partition_file,
                   include_seed=False, index_name="bodyId"):
    """Load the given key and partition data as a dataframe
    whose index is the bodyIds and a single column giving the cluster
    id for each neuron. The column name will be either `chi` or `(chi, seed)`
    (inferred from the partition file name) depending on `include_seed`"""
    key_file = Path(key_file).resolve()
    partition_file = Path(partition_file).resolve()
    key_type, key_name = _get_filename_parts(key_file)
    partition_type, partition_name, info = _get_filename_parts(partition_file)
    assert key_type == "key", f"Key file {key_file} does not appear to be a key"
    assert partition_type == "partition", f"Partition file {partition_file} does not appear to be a partition file"
    assert key_name == partition_name, f"Key name {key_name} does not match partition name {partition_name}"
    seed, chi, tmp = info.split("-", maxsplit=2)
    seed = int(seed)
    chi = float(chi)
    with open(key_file, "r") as kf, open(partition_file, "r") as pf:
        df = pd.DataFrame([(int(key.strip()), int(cluster.strip())) for key, cluster in zip(kf.readlines(), pf.readlines())])
    df = df.set_index(0)
    if include_seed:
        df.columns = pd.Index([(chi, seed)])
    else:
        df.columns = [chi]
    df.index.name = index_name
    return df


def get_available_clustering(clustering_dir="../results/clustering"):
    """Look for files named 'partition_[name]_[seed]-[chi]-[id] in the
    specified directory and return a dataframe with info.
    
    The default `clustering_dir` assumes you are working with a script
    or notebook in the /scripts folder of the kuninlab project template."""
    available = []
    for file in [f for f in os.listdir(clustering_dir) if f.startswith("partition")]:
        try:
            prefix, name, suffix = _get_filename_parts(file)
            try:
                seed, chi, tmp = suffix.split("-", maxsplit=2)
                seed = int(seed)
                chi = float(chi)
            except ValueError:
                continue
            available.append((name, chi, seed, tmp, Path(clustering_dir, file)))
        except ValueError:
            continue
    all_files = pd.DataFrame(available, columns=["name", "chi", "seed", "id", "file"]).sort_values(["name","chi"])
    return all_files


def load_selected_runs(selected_runs: dict | str | Path,
                       preprocessed_dir="../data/preprocessed",
                       clustering_dir="../results/clustering",
                       ext="txt",
                       **kwargs):
    """Load the partitions specified into one big dataframe.
    If `selected_runs` is a string or a path, it should point to a json file.
    Otherwise, it assumes that `selected_runs` is a `dict`.
    
    The dict should have the following structure:
    {
        'name': 'name of run',
        'runs': [{'chi': chi_value,
                  'seeds': [list of seeds]},
                 ...
                ]
    }"""
    if not isinstance(selected_runs, dict):
        with open(selected_runs, "r") as jsonfile:
            selected_runs = json.load(jsonfile)
    available = get_available_clustering(clustering_dir=clustering_dir)
    parts = []
    name = selected_runs["name"]
    key_file = Path(preprocessed_dir, f"key_{name}.{ext}")
    for run in selected_runs["runs"]:
        matches = available.query(f"name == '{name}' & chi == {run['chi']} & seed.isin({run['seeds']})")
        for partition_file in matches['file']:
            current_partition = load_partition(key_file,
                                            partition_file,
                                            include_seed=(len(run['seeds']) > 1),
                                            **kwargs)
            parts.append(current_partition)
    nodes = pd.concat(parts, axis=1)
    return nodes