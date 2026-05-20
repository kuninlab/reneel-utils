#!/opt/anaconda3/bin/python
"""
Usage idea:
$ python data.py /data
$ python format_edgelist.py data/edgelist_file [more args]
$ python run_reneel data/edgelist_file --chi 0.0 --nruns 10
result would be that reneel is run 10 times, each time with a different
random seeds.
"""
import argparse, logging
import os, shutil
import tomllib
from pathlib import Path
import subprocess
import time
from itertools import cycle, product
from secrets import randbits, token_hex
from tempfile import TemporaryDirectory
from dataclasses import dataclass, field, asdict
from datetime import datetime

from util import MyArgumentParser, parse_toml_args, merge_args, remap_paths_for_docker


@dataclass
class ReneelRun:
    """Class tracking input and output files to a run of reneel"""
    edgelist_file: Path
    seed: int
    chi: float
    rg_ensemble_size: int
    reneel_ensemble_size: int
    rg_parameter: int = 2
    # clean_file: Path = None
    # degree_file: Path = None
    # info_file: Path = None
    partition_file: Path = None
    results_file: Path = None
    associated_files: list = field(default_factory=list)
    wall_time: float = None
    completed_process: subprocess.CompletedProcess = None

    def __post_init__(self):
        self.edgelist_file = Path(self.edgelist_file)
        if not self.edgelist_file.exists():
            raise FileNotFoundError(f"Missing edgelist file {self.edgelist_file}")
        for prefix in ["clean_", "degree_", "info_"]:
            file = self.edgelist_file.with_stem(f"{prefix}{self.edgelist_file.stem}")
            if not file.exists():
                raise FileNotFoundError(f"Can't find associated file {file}")
            self.associated_files.append(file)
        # self.clean_file = self.edgelist_file.with_stem(f"clean_{self.edgelist_file.stem}")
        # self.degree_file = self.edgelist_file.with_stem(f"degree_{self.edgelist_file.stem}")
        # self.info_file = self.edgelist_file.with_stem(f"info_{self.edgelist_file.stem}")
    

    def __str__(self):
        return "\n".join(f"{k}: {v}" for k,v in asdict(self).items())


def seed_generator(seeds=None):
    """Return seeds for rng, either by cycling through the provided list indefinitely
    or producing a new random seed each time"""
    if seeds is None:
        for _ in cycle([1]):
            yield randbits(32)
    else:
        for s in cycle(seeds):
            yield s


def ensure_dir_exists(path):
    """Checks if the given directory exists. If not, creates it."""
    _path = Path(path).resolve()
    if not _path.is_dir():
        os.makedirs(_path)
    return None


def run_reneel_and_collect_output(path_to_executable,
                                  output_dir,
                                  reneel_run: ReneelRun,
                                  keep_results=False, test_mode=False,
                                  n_cpu=os.cpu_count()):
    """Run reneel in the input file's directory without copying input files.

    Uses a random hex ID to uniquely name output files, replacing the old
    temp-directory name that served the same purpose.
    """
    rg_ensemble_per_cpu = max(reneel_run.rg_ensemble_size // n_cpu, 1)
    if rg_ensemble_per_cpu * n_cpu != reneel_run.rg_ensemble_size:
        logging.warning(f"Using rg ensemble size {rg_ensemble_per_cpu * n_cpu}; expected {reneel_run.rg_ensemble_size} but {n_cpu = }")
    reneel_ensemble_per_cpu = max(reneel_run.reneel_ensemble_size // n_cpu, 1)
    if reneel_ensemble_per_cpu * n_cpu != reneel_run.reneel_ensemble_size:
        logging.warning(f"Using reneel iteration size {reneel_ensemble_per_cpu * n_cpu}; expected {reneel_run.reneel_ensemble_size} but {n_cpu = }")

    current_dir = os.getcwd()
    _output_dir = Path(output_dir)
    ensure_dir_exists(_output_dir)
    _output_dir = _output_dir.resolve()
    _path_to_executable = Path(path_to_executable).resolve()

    run_id = token_hex(4)
    tmp_suffix = f"{reneel_run.seed}-{reneel_run.chi}-{run_id}"

    input_file = reneel_run.edgelist_file.resolve()
    input_dir = input_file.parent

    partition_file = input_file.with_stem(f"partition_{input_file.stem}")
    output_partition_file = Path(_output_dir, partition_file.with_stem(f"{partition_file.stem}_{tmp_suffix}").name)
    results_file = input_file.with_stem(f"results_{input_file.stem}")
    output_results_file = Path(_output_dir, results_file.with_stem(f"{results_file.stem}_{tmp_suffix}").name)

    cmd = [_path_to_executable, reneel_run.rg_parameter, rg_ensemble_per_cpu, reneel_ensemble_per_cpu, reneel_run.seed, reneel_run.chi, input_file.name]
    if test_mode:
        cmd = ['echo'] + cmd
    cmd = list(map(str, cmd))
    logging.debug(f"Input directory: {input_dir}\ncmd: {' '.join(cmd)}")

    if test_mode:
        with open(partition_file, "a") as pf:
            print("Testing", reneel_run.seed, reneel_run.chi, file=pf)
        with open(results_file, "a") as rf:
            print("Testing", reneel_run.seed, reneel_run.chi, file=rf)

    os.chdir(input_dir)
    t_start = time.perf_counter()
    reneel_run.completed_process = subprocess.run(cmd)
    t_end = time.perf_counter()
    reneel_run.wall_time = t_end - t_start
    os.chdir(current_dir)

    if reneel_run.completed_process.returncode:
        logging.warning(f"Process returned error code {reneel_run.completed_process.returncode}:\n{reneel_run.completed_process}")

    logging.debug(f"Moving {partition_file} to {output_partition_file}")
    shutil.move(partition_file, output_partition_file)
    if keep_results:
        logging.debug(f"Moving {results_file} to {output_results_file}")
        shutil.move(results_file, output_results_file)

    reneel_run.partition_file = output_partition_file
    if keep_results:
        reneel_run.results_file = output_results_file
    return None


def run_reneel_and_collect_output_with_temp(path_to_executable,
                                            output_dir,
                                            reneel_run: ReneelRun,
                                            keep_results=False, test_mode=False,
                                            n_cpu=os.cpu_count()):
    """Create a temporary directory, copy the input files there, then run reneel.

    Kept for backward compatibility. For large input files prefer
    run_reneel_and_collect_output, which avoids copying input data.
    """
    rg_ensemble_per_cpu = max(reneel_run.rg_ensemble_size // n_cpu, 1)
    if rg_ensemble_per_cpu * n_cpu != reneel_run.rg_ensemble_size:
        logging.warning(f"Using rg ensemble size {rg_ensemble_per_cpu * n_cpu}; expected {reneel_run.rg_ensemble_size} but {n_cpu = }")
    reneel_ensemble_per_cpu = max(reneel_run.reneel_ensemble_size // n_cpu, 1)
    if reneel_ensemble_per_cpu * n_cpu != reneel_run.reneel_ensemble_size:
        logging.warning(f"Using reneel iteration size {reneel_ensemble_per_cpu * n_cpu}; expected {reneel_run.reneel_ensemble_size} but {n_cpu = }")

    current_dir = os.getcwd()
    _output_dir = Path(output_dir)
    ensure_dir_exists(_output_dir)
    _output_dir = _output_dir.resolve()
    _path_to_executable = Path(path_to_executable).resolve()
    with TemporaryDirectory(dir=current_dir) as tmpdir:
        logging.debug(f"Created temporary directory {tmpdir}")
        tmp_suffix = f"{reneel_run.seed}-{reneel_run.chi}-{Path(tmpdir).parts[-1]}"
        shutil.copy(reneel_run.edgelist_file, tmpdir)
        for file in reneel_run.associated_files:
            shutil.copy(file, tmpdir)
        os.chdir(tmpdir)
        _input_file = Path(tmpdir, reneel_run.edgelist_file.name).resolve()
        partition_file = _input_file.with_stem(f"partition_{_input_file.stem}")
        output_partition_file = Path(_output_dir, partition_file.with_stem(f"{partition_file.stem}_{tmp_suffix}").name)
        results_file = _input_file.with_stem(f"results_{_input_file.stem}")
        output_results_file = Path(_output_dir, results_file.with_stem(f"{results_file.stem}_{tmp_suffix}").name)

        cmd = [_path_to_executable, reneel_run.rg_parameter, rg_ensemble_per_cpu, reneel_ensemble_per_cpu, reneel_run.seed, reneel_run.chi, _input_file.name]
        if test_mode:
            cmd = ['echo'] + cmd
        cmd = list(map(str, cmd))
        logging.debug(f"Current directory: {os.getcwd()}\ncmd: {' '.join(cmd)}")
        if test_mode:
            with open(partition_file, "a") as pf:
                print("Testing", reneel_run.seed, reneel_run.chi, file=pf)
            with open(results_file, "a") as rf:
                print("Testing", reneel_run.seed, reneel_run.chi, file=rf)
        t_start = time.perf_counter()
        reneel_run.completed_process = subprocess.run(cmd)
        t_end = time.perf_counter()
        reneel_run.wall_time = t_end - t_start

        if reneel_run.completed_process.returncode:
            logging.warning(f"Process returned error code {reneel_run.completed_process.returncode}:\n{reneel_run.completed_process}")

        logging.debug(f"Copying {partition_file} to {output_partition_file}")
        shutil.copy(partition_file, output_partition_file)
        if keep_results:
            logging.debug(f"Copying {results_file} to {output_results_file}")
            shutil.copy(results_file, output_results_file)
        os.chdir(current_dir)
    reneel_run.partition_file = Path(_output_dir, partition_file.name)
    if keep_results:
        reneel_run.results_file = Path(_output_dir, results_file.name)
    return None


_DEFAULTS = {
    "verbose":              "warn",
    "chi":                  [0.0],
    "nruns":                1,
    "seed":                 None,
    "nproc":                os.cpu_count(),
    "rg_ensemble_size":     10,
    "reneel_ensemble_size": 8,
    "rg_parameter":         2,
    "reneelpath":           "a.out",
    "output":               None,
    "logfile":              "reneel.log",
    "keepresults":          False,
    "test":                 False,
    "docker":               False,
}

if __name__ == "__main__":
    ap = MyArgumentParser(description="""Run the reneel executable one or more times.
                                 This could probably just be a bash script but here we are.""",
                                 fromfile_prefix_chars="@")
    ap.add_argument("file", nargs="*", default=None,  #dest="input",
                    help="formatted edgelist file (deprecated positional form; use --input instead)")
    ap.add_argument("-t", "--test", action="store_true", default=None,
                    help="Run tests only. Replaces execution of reneel program with echo statement and creates test output files.")

    io_group = ap.add_argument_group("Inputs and outputs", "Control input/output")
    io_group.add_argument("-i", "--input", nargs="*", default=None,
                    help="Formatted edgelist file(s)")
    io_group.add_argument("--config", default=None,
                    help="Pass arguments via configuration file. Commandline args take precedence.")
    io_group.add_argument("-o", "--output", dest="output", default=None,
                    help="Directory to store output. Defaults to current working directory")
    io_group.add_argument("--outputdir", dest="output", default=None, 
                    help="Deprecated alias for --output")
    io_group.add_argument("-k", "--keepresults", action="store_true", default=None,
                    help="Pass to keep results_[file] from reneel output")
    io_group.add_argument("-l", "--logfile", default=None,
                    help="Write the CompletedProcess objects to this file")
    io_group.add_argument("-v", "--verbose",
                          choices=["debug", "info", "warn", "error", "critical"],
                          default=None,
                          help="How verbose the output should be, from most verbose to least verbose. Default is 'warn'")
    io_group.add_argument("--docker", action="store_true", default=None,
                    help="Remap input paths to /data/<filename> for Docker execution")

    qg_group = ap.add_argument_group("Qg and reneel configuration", "chi, runs, etc")
    qg_group.add_argument("-c", "--chi", default=None,
                    nargs="+", type=float,
                    help="Chi value(s) to use")
    qg_group.add_argument("-n", "--nruns", type=int, default=None,
                    help="Number of times to run each chi value")
    qg_group.add_argument("-s", "--seed", nargs="+", type=int, default=None,
                          help="Seed for random number generation. Multiple seeds will be cycled through for each individual call to reneel. If not specified, seeds will be generated randomly")

    ex_group = ap.add_argument_group("Reneel arguments", "arguments passed to reneel executable")
    ex_group.add_argument("-x", "--reneelpath", default=None,  # x for executable
                    help="Path to reneel executable. Default is 'a.out'")
    ex_group.add_argument("-p", "--nproc", type=int, default=None,
                    help="Number of processors used")
    ex_group.add_argument("-e", "--rg-ensemble-size", type=int, default=None,
                    help="Ensemble size for randomized greedy portion of the algorithm")
    ex_group.add_argument("-f", "--reneel-ensemble-size", type=int, default=None,
                    help="Ensemble size for reneel iteration")
    ex_group.add_argument("-g", "--rg-parameter", type=int, default=None,
                    help="Parameter for randomized greedy algorithm (default 2)")

    cli_args = ap.parse_args()
    cfg = parse_toml_args(cli_args.config, Path(__file__).stem)

    # Merge: explicit CLI > TOML > defaults
    args = merge_args(cli_args, cfg, _DEFAULTS)

    # output defaults to cwd after merge (not set at parse time so TOML can override it)
    if not args["output"]:
        args["output"] = os.getcwd()

    logging.basicConfig(format="%(asctime)s %(levelname)s %(module)s\t%(message)s",
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=getattr(logging, args["verbose"].upper()))
    logging.debug(f"Commandline arguments:   {cli_args}")
    logging.debug(f"Final configuration:     {args}")

    # Handoff: if no input given, look for it in the format_edgelist section of the same config
    if not args["input"]:
        fe_cfg = parse_toml_args(cli_args.config, "format_edgelist")
        if fe_cfg:
            args["input"] = fe_cfg.get("input") or fe_cfg.get("file")
            if args["input"]:
                logging.info(f"Inferred input from [format_edgelist] config: {args['input']}")
        if not args["input"]:
            ap.error("No input files given and could not infer from [format_edgelist] config.")

    if args["docker"]:
        remap_paths_for_docker(args, output_dir="/results")

    ensure_dir_exists(Path(args["logfile"]).parent)

    with open(args["logfile"], "a") as logfile:
        for (chi, file, run_number), seed in zip(product(args["chi"], args["input"], range(args["nruns"])), seed_generator(seeds=args["seed"])):
            logging.info(f"Iteration {chi}-{file}-{run_number}")
            reneelrun = ReneelRun(edgelist_file=file, seed=seed, chi=chi,
                                  rg_ensemble_size=args["rg_ensemble_size"],
                                  reneel_ensemble_size=args["reneel_ensemble_size"],
                                  rg_parameter=args["rg_parameter"])
            run_reneel_and_collect_output(args["reneelpath"], args["output"], reneelrun, args["keepresults"], test_mode=args["test"], n_cpu=args["nproc"])
            print(f"{datetime.now():%m/%d/%Y %I:%M:%S %p} test = {args['test']}\n",
                  reneelrun, file=logfile)