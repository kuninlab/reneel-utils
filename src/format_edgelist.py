#!/opt/anaconda3/bin/python
"""Format an edgelist for use with the generalized modularity density code.
This will take the given edgelist and renumber the nodes 1...N,
where N is the number of unique nodes in the graph.

Output is two files, one has prefix clean_ and one has prefix key_.
[prefix]_[filename] has the renumbered edgelist
key_[filename] has the mapping from original node index to new node index

See https://github.com/prameshsingh/generalized-modularity-density"""
import argparse
from pathlib import Path
import logging
from collections import Counter
import shutil
import pandas as pd
import os

class AddDict(dict):
    """If `key` is missing, set the default value to `0.0`
    Useful for adding up edge weights"""
    def __missing__(self, key):
        return 0


def read_graph(source: Path, sep=None, skip=0,
               directed=False,
               convert=int, weight_convert=int,
               u_col=0, v_col=1, w_col=2):
    """Read a graph from an edgelist file. Combine parallel edges by summing their weights;
    if `directed=False` also combine antiparallel edges.
    
    Returns:
    nodes : a dict of node:weight pairs (total weight of incident edges)
    degrees : a dict of a node:degree pairs (total number of incident edges)
    edges: a dict of (v1,v2):weight pairs"""
    logging.info(f"Reading file {source.resolve()}, skipping {skip} line(s), splitting at {sep=}")
    # nodes = set()
    nodes = AddDict()
    degrees = Counter()
    edges = AddDict()
    with open(source, "r") as f:
        for lineno, line in enumerate(f.readlines()[skip:], start=1):
            if line.strip():
                try:
                    # u, v, w = line.split(sep=sep)
                    ls = line.split(sep=sep)
                    u, v, w = ls[u_col], ls[v_col], ls[w_col]
                except Exception as ex:
                    logging.critical(f"Failed to split line {lineno + skip} using separator {sep=}\nOffending line: {line}\nError: {ex}")
                    exit(1)
                u, v, w = convert(u.strip()), convert(v.strip()), weight_convert(w.strip())
                if not directed:
                    u, v = max(u,v), min(u,v)
                if u != v:
                    nodes[u] += w
                    nodes[v] += w
                    degrees[u] += 1
                    degrees[v] += 1
                    edges[(u,v)] += w
                else:
                    logging.debug(f"Ignoring self-loop {u} - {v} on line {lineno + skip}")

    return nodes, degrees, edges


def write_edges(output_file: Path, edges: dict, mapper: dict):
    """Write the formatted edgelist file"""
    # output_file = output_file.with_stem(output_file.stem + suffix)
    with open(output_file, "w") as dest:
        logging.info(f"Writing formatted, renumbered edgelist to {output_file.resolve()}")
        for e, w in edges.items():
            print(f"{mapper[e[0]]} {mapper[e[1]]} {w}", file=dest)


def write_key(key_file: Path, mapper: dict):
    """Write the format key. Each line is `original_id formatted_id`"""
    # key_file = key_file.with_stem(key_file.stem + "_key")
    with open(key_file, "w") as dest:
        logging.info(f"Writing mapping to {key_file.resolve()}")
        for k, v in mapper.items():
            print(f"{k} {v}", file=dest)


def write_simple_key(key_file: Path, nodes):
    """Write the nodes in sorted order"""
    with open(key_file, "w") as dest:
        logging.info(f"Writing node list to {key_file.resolve()}")
        for k in sorted(nodes):
            print(k, file=dest)


def read_key(key_file:Path, cvt=int):
    """Read the format key from a file and store it as a dict
    Assumes each line is `original_id formatted_id`
    `formatted_id` is always an int, but `cvt` will be used to convert `original_id` to the specified type."""
    with open(key_file, "r") as source:
        unmapper = {int(l.split()[1].strip()): cvt(l.split()[0].strip()) for l in source.readlines() if l.strip()}
    return unmapper


def write_info(info_file: Path, nodes, edges):
    """Write the info file, which simply has the number of nodes and number of edges in the network
    (Note, this is number of edges, ignoring weight)"""
    with open(info_file, "w") as dest:
        logging.info(f"Writing info file to {info_file.resolve()}")
        print(f"{len(nodes)} {len(edges)}", file=dest)


def write_degree(degree_file: Path, nodes: dict, degrees: dict):
    """Write the degree file.
    Each line has the unweighted and weighted degree of a node, in sorted order."""
    with open(degree_file, "w") as dest:
        logging.info(f"Writing degree file to {degree_file.resolve()}")
        for v in sorted(nodes):
            print(f"{degrees[v]} {nodes[v]}", file=dest)


def load_partition(file_stem, chi, seed=17289,
                   key_dir=None,
                   dir=None,  existing_df: pd.DataFrame=None,
                   index_name="bodyId", default_extension=".csv",
                   old_format=False):
    """Try to load partition data. This amounts to finding several files and combining them.
    The assumed directory structure is '[dir]/[seed]/[chi]/partition_[file_stem]' for the partition
    and '[dir]/[seed]/[chi]/key_[file_stem]' for the key (to map node numbers to bodyIds)

    The files are 'partition_[file_stem]' and either 'key_[file_stem]' or '[file_stem]_key'
    It looks for the former if `old_format=False` (the default) and the latter if True.
    
    If an existing dataframe is passed, merge information into it."""
    # try to find partition_file_stem and key_file_stem
    if dir is None:
        dir = Path(os.getcwd())
    if key_dir is None:
        key_dir = dir
    if index_name is None:
        index_name = existing_df.index.name
    
    # check if file_stem has a file extension
    if seed is None:
        seed = ""
    else:
        seed = str(seed)
    filepath = Path(dir, seed, str(chi), file_stem)
    if len(filepath.suffix) == 0:
        filepath = filepath.with_suffix(default_extension)
    
    partition_file = filepath.with_stem("partition_" + filepath.stem)
    
    if old_format:
        key_file = filepath.with_stem(filepath.stem.replace("_formatted", "_key"))
    else:
        key_file = filepath.with_stem("key_" + filepath.stem)
    if not key_file.exists():
        # try looking in a different directory
        key_file = Path(key_dir, key_file.name)
    
    logging.info(f"Attempting to use partition file {partition_file.resolve()}")
    logging.info(f"Attempting to use key file       {key_file.resolve()}")
    
    unmapper = read_key(key_file)
    df = pd.DataFrame.from_dict(unmapper, orient="index", columns=[index_name])
    df[chi] = 0
    with open(partition_file, "r") as part:
        for i, l in enumerate(part.readlines(), start=1):
            df.loc[i][chi] = int(l.strip())
    df = df.set_index(index_name)
    if existing_df is not None:
        merged = existing_df.merge(df, left_index=True, right_index=True, how="outer", suffixes=["", f"_{file_stem}"])
        # col = if f"{chi}_{file_stem}" in merged.columns else f"{chi}"
        col = f"{chi}_{file_stem}"
        if col not in merged.columns:
            col = f"{chi}"
        merged[col] = merged[col].fillna(0).astype(int)
        return merged
    else:
        return df

def add_underscore_to_prefix(pre: str):
    if len(pre) > 0 and not pre.endswith("_"):
        return f"{pre}_"
    return pre


def add_underscore_to_suffix(suf: str):
    if len(suf) > 0 and not suf.startswith("_"):
        return f"_{suf}"
    return suf


def format_for_reneel(args):
    logging.debug(args)
    reserved_prefixes = ["clean_", "key_", "degree_", "info_", "original_"]
    original_prefix = add_underscore_to_prefix(args.inprefix)
    original_suffix = add_underscore_to_suffix(args.insuffix)
    prefix = add_underscore_to_prefix(args.prefix)
    suffix = add_underscore_to_suffix(args.suffix)
    # if len(prefix) > 0 and not prefix.endswith("_"):
    #     prefix = prefix + "_"
    # if len(suffix) > 0 and not suffix.startswith("_"):
    #     suffix = "_" + suffix
    # if len(prefix) == 0 and len(suffix) == 0:
    #     logging.warning(f"No prefix or suffix entered; this will overwrite the original file! A copy will be made automatically.")
    if prefix in reserved_prefixes:
        logging.critical(f"Cannot use '{prefix}' as prefix (reserved prefixes: {reserved_prefixes})")
        exit(1)

    sep = {"space": None,
        "comma": ",",
        "semicolon": ";"}.get(args.sep, None)
    cvt = {"int": int,
           "str": str,
           "float": float}.get(args.convert, int)
    wcvt = {"int": int,
            "float": float}.get(args.wtype, int)

    for file in args.file:
        source_path = Path(file).resolve()
        origin_name = source_path.stem.replace(original_prefix, "").replace(original_suffix, "")
        # copy_file = source_path.with_stem(f"original_{source_path.stem}{suffix}")
        # copy_file = source_path.with_stem(f"original_{origin_name}{suffix}")
        # if args.copy or len(prefix) == 0:
        #     logging.debug(f"Creating a copy ({copy_file}) of the input file ({source_path})")
        #     shutil.copyfile(source_path, copy_file)
        
        if args.outputdir is None:
            outputdir = Path(source_path.parent)
            logging.debug(f"Inferred output directory {outputdir.resolve()}")
        else:
            outputdir = Path(args.outputdir)
        if not outputdir.is_dir():
            logging.debug(f"Attempting to create directory {outputdir.resolve()}")
            os.makedirs(outputdir)
        # output_file = source_path.with_stem(prefix + source_path.stem + suffix)
        # clean_file = source_path.with_stem("clean_" + source_path.stem + suffix)
        # key_file = source_path.with_stem("key_" + source_path.stem + suffix)
        # info_file = source_path.with_stem("info_" + source_path.stem + suffix)
        # degree_file = source_path.with_stem("degree_" + source_path.stem + suffix)
        output_file = Path(outputdir, source_path.name).with_stem(f"clean_{origin_name}{suffix}")
        # clean_file = Path(outputdir, source_path.name).with_stem(f"clean_{origin_name}{suffix}")
        key_file = Path(outputdir, source_path.name).with_stem(f"key_{origin_name}{suffix}")
        info_file = Path(outputdir, source_path.name).with_stem(f"info_{origin_name}{suffix}")
        degree_file = Path(outputdir, source_path.name).with_stem(f"degree_{origin_name}{suffix}")

        # output_file = Path(outputdir, source_path.name).with_stem(f"{prefix}{origin_name}{suffix}")


        # load the graph into memory
        nodes, degrees, edges = read_graph(source_path, sep=sep, skip=args.skip,
                                        directed=args.directed, convert=cvt, weight_convert=wcvt,
                                        u_col=args.u_col, v_col=args.v_col, w_col=args.w_col)
        logging.info(f"Read in {len(nodes)} nodes and {len(edges)} edges")
        # mapper = dict(zip(sorted(nodes.keys()), range(1, len(nodes) + 1)))
        mapper = {v: i for i, v in enumerate(sorted(nodes), start=1)}

        write_edges(output_file, edges, mapper)
        # logging.debug(f"Creating 'clean_' copy ({clean_file}) for reneel executable")
        # shutil.copyfile(output_file, clean_file)
        # write_key(key_file, mapper)
        write_simple_key(key_file, nodes)
        write_info(info_file, nodes, edges)
        write_degree(degree_file, nodes, degrees)



if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="""Format an edgelist for use with the generalized modularity density program.
This will take the given edgelist and renumber the nodes 1...N,
where N is the number of unique nodes in the graph. Moreover, it will sum
weights of parallel edges. By default it also combines antiparallel edges,
retulting in an undirecetd graph.

This modifies the file in place. To keep a copy of the original file, use the --copy flag.
The original file can be recovered using the modified file and they key file, described below.
This modified file is also copied to `clean_[file]` (for compatibility with the reneel program).
In addition, it outputs files with prefixes `key_`, `info_`, `degree_`
There are three additional files:
key_[filename]_[suffix] has the mapping from original node index to new node index.
info_[filename]_[suffix] has the number of nodes and number of edges in the network.
degree_[filename]_[suffix] has the degree and weighted degree of each node.


See https://github.com/prameshsingh/generalized-modularity-density for more information.
This python script is an attempt to reverse-engineer the `work.sh` file.""",
    epilog="""The workflow for using this file looks like this:
    
    $ python format_edgelist edgelist.csv --sep comma
    $ reneel [params] edgelist.csv""")
    ap.add_argument("file", nargs="+",
                    help="Edge list file")
    ap.add_argument("-o", "--outputdir",
                    help="Output directory (will be created if needed)")
    ap.add_argument("--inprefix", default="",
                    help="Assumes input filename is of the form [inprefix]_[file]_[insuffix].[ext]. For purposes of naming outputs, will ignore [inprefix]")
    ap.add_argument("--insuffix", default="",
                    help="Assumes input filename is of the form [inprefix]_[file]_[insuffix].[ext]. For purposes of naming outputs, will ignore [insuffix]")
    ap.add_argument("-p", "--prefix", default="",
                    help="Output file will be named [prefix]_[file]_[suffix].[ext]. Underscore is optional, and won't be included if prefix is empty.")
    ap.add_argument("-s", "--suffix", default="",
                    help="Output file will be named [prefix]_[file]_[suffix].[ext]. Underscore is optional, and won't be included if suffix is empty.")
    # ap.add_argument("--name", default="_formatted",
    #                 help="Output file will be named [file]_[suffix].[ext]. Default is 'formatted'. Underscore is optional.")
    # ap.add_argument("--copy", action="store_true",
    #                 help="Create a copy of the input file, called 'original_[file]'.")
    ap.add_argument("--skip",
                    type=int, default=0,
                    help="Number of rows in the edgelist file to skip (useful if the file has a header row)")
    ap.add_argument("--sep",
                    choices=["space", "comma", "semicolon"], default="space",
                    help="How to split rows of the input file. By default, `l.split()` is used which splits at whitespace (see python docs for more info); using --s comma will use `l.split(',')`. This can be used if reading, e.g. a csv file.")
    ap.add_argument("--verbose",
                    choices=["debug", "info", "warn", "error", "critical"],
                    default="warn",
                    help="How verbose the output should be, from most verbose to least verbose. Default is 'warn'")
    ap.add_argument("-d", "--directed", action="store_true",
                    help="Preserve edge direction")
    ap.add_argument("-c", "--convert", choices=["int", "str", "float"],
                    default="int",
                    help="How to parse nodes. Default is int")
    ap.add_argument("--wtype", choices=["int", "float"],
                    default="int",
                    help="How to parse weights. Default is int.")
    ap.add_argument('-u', '--u_col', type=int, default=0,
                    help="Which column contains the source node of each edge. Default 0 for first column.")
    ap.add_argument('-v', '--v_col', type=int, default=1,
                    help="Which column contains the target node of each edge. Default 1 for second column")
    ap.add_argument('-w', '--w_col', type=int, default=2,
                    help="Which column contains the edge weight. Default 2 for third column")
    args = ap.parse_args()

    logging.basicConfig(format="%(asctime)s %(levelname)s\t%(message)s",
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=getattr(logging, args.verbose.upper()))
    
    format_for_reneel(args)
