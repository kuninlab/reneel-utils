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
from pathlib import Path
import subprocess
import time
from itertools import cycle, product
from secrets import randbits
from tempfile import TemporaryDirectory
from dataclasses import dataclass, field, asdict
from datetime import datetime

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


def run_reneel_and_collect_output(path_to_executable, 
                                  output_dir,
                                  reneel_run: ReneelRun,
                                  keep_results=False, test_mode=False,
                                  n_cpu=os.cpu_count()):
    """Create a temporary directory, copy the input files there, then run reneel.
    Copy the output partition to the output directory"""
    rg_ensemble_per_cpu = max(reneel_run.rg_ensemble_size // n_cpu, 1)
    if rg_ensemble_per_cpu * n_cpu != reneel_run.rg_ensemble_size:
        logging.warning(f"Using rg ensemble size {rg_ensemble_per_cpu * n_cpu}; expected {reneel_run.rg_ensemble_size} but {n_cpu = }")
    reneel_ensemble_per_cpu = max(reneel_run.reneel_ensemble_size // n_cpu, 1)
    if reneel_ensemble_per_cpu * n_cpu != reneel_run.reneel_ensemble_size:
        logging.warning(f"Using reneel iteration size {reneel_ensemble_per_cpu * n_cpu}; expected {reneel_run.reneel_ensemble_size} but {n_cpu = }")
    
    current_dir = os.getcwd()
    _output_dir = Path(output_dir)
    if not _output_dir.is_dir():
        logging.debug(f"Creating directory {_output_dir}")
        os.makedirs(_output_dir)
    _output_dir = _output_dir.resolve()
    _path_to_executable = Path(path_to_executable).resolve()
    with TemporaryDirectory(dir=current_dir) as tmpdir:
        logging.debug(f"Created temporary directory {tmpdir}")
        tmp_suffix = f"{reneel_run.seed}-{reneel_run.chi}-{Path(tmpdir).parts[-1]}"
        # copy the input file and associated files
        shutil.copy(reneel_run.edgelist_file, tmpdir)
        for file in reneel_run.associated_files:
            shutil.copy(file, tmpdir)
        os.chdir(tmpdir)
        _input_file = Path(tmpdir, reneel_run.edgelist_file.name).resolve()
        partition_file = _input_file.with_stem(f"partition_{_input_file.stem}")
        output_partition_file = Path(_output_dir, partition_file.with_stem(f"{partition_file.stem}_{tmp_suffix}").name)
        results_file = _input_file.with_stem(f"results_{_input_file.stem}")
        output_results_file = Path(_output_dir, results_file.with_stem(f"{results_file.stem}_{tmp_suffix}").name)
        
        cmd = [_path_to_executable,  reneel_run.rg_parameter, rg_ensemble_per_cpu, reneel_ensemble_per_cpu, reneel_run.seed, reneel_run.chi, _input_file.name]
        if test_mode:
            cmd = ['echo'] + cmd
        cmd = list(map(str, cmd))
        logging.debug(f"Current directory: {os.getcwd()}\ncmd: {' '.join(cmd)}")
        # print("Got to the point that we would try subprocess.run on", cmd)
        if test_mode:
            with open(partition_file, "a") as pf:
                print("Testing", reneel_run.seed, reneel_run.chi, file=pf)
            with open(results_file, "a") as rf:
                print("Testing", reneel_run.seed, reneel_run.chi, file=rf)
        t_start = time.perf_counter()
        reneel_run.completed_process = subprocess.run(cmd)
        t_end = time.perf_counter()
        reneel_run.wall_time = t_end - t_start

        if reneelrun.completed_process.returncode:
            logging.warning(f"Process returned error code {reneelrun.completed_process.returncode}:\n{reneelrun.completed_process}")

        # print(reneel)
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="""Run the reneel executable one or more times.
                                 This could really be a bash script. Note that one of -r or -s is required.""")
    ap.add_argument("file", nargs="+", help="formatted edgelist file")
    ap.add_argument("-o", "--outputdir", default=os.getcwd(),
                    help="Directory to store output. Defaults to current working directory")
    ap.add_argument("-c", "--chi", default=[0.0],
                    nargs="+", type=float,
                    help="Chi value(s) to use")
    ap.add_argument("-n", "--nruns", type=int, default=1,
                    help="Number of times to run each chi value")
    seed = ap.add_mutually_exclusive_group(required=True)
    seed.add_argument("-s", "--seed", nargs="+",
                      type=int,
                      help="Seed for random number generation. Multiple seeds will be cycled through for each individual call to reneel. Cannot be used with -r")
    seed.add_argument("-r", "--random", action="store_true",
                      help="Generate random seeds for each run. Cannot be used with -s")
    ap.add_argument("-p", "--nproc", type=int, default=os.cpu_count(),
                    help="Number of processors used")
    ap.add_argument("-x", "--reneelpath", default="a.out",  # x for executable
                    help="Path to reneel executable. Default is 'a.out'; assumes executable is in the same directory as the input files.")
    ap.add_argument("-k", "--keepresults", action="store_true",
                    help="Pass to keep results_[file] from reneel output")
    ap.add_argument("-e", "--rg-ensemble-size", type=int, default=10,
                    help="Ensemble size for randomized greedy portion of the algorithm")
    ap.add_argument("-f", "--reneel-ensemble-size", type=int, default=8,
                    help="Ensemble size for reneel iteration")
    ap.add_argument("-g", "--rg-parameter", type=int, default=2,
                    help="Parameter for randomized greedy algorithm (default 2)")
    ap.add_argument("-l", "--logfile", default="reneel.log",
                    help="Write the CompletedProcess objects to this file")
    ap.add_argument("-v", "--verbose",
                    choices=["debug", "info", "warn", "error", "critical"],
                    default="warn",
                    help="How verbose the output should be, from most verbose to least verbose. Default is 'warn'")
    ap.add_argument("-t", "--test", action="store_true",
                    help="Run tests only. Replaces execution of reneel program with echo statement and creates test output files.")
    args = ap.parse_args()
    logging.basicConfig(format="%(asctime)s %(levelname)s\t%(message)s",
                        datefmt='%m/%d/%Y %I:%M:%S %p',
                        level=getattr(logging, args.verbose.upper()))
    logging.debug(f"Parameters: {args}")
    reneelpath = Path(args.reneelpath).resolve()

    with open(args.logfile, "a") as logfile:
        for (chi, file, run_number), seed in zip(product(args.chi, args.file, range(args.nruns)), seed_generator(seeds=args.seed)):
            # print("iteration:", chi, file, run_number)
            logging.info(f"Iteration {chi}-{file}-{run_number}")
            reneelrun = ReneelRun(edgelist_file=file, seed=seed, chi=chi,
                                  rg_ensemble_size=args.rg_ensemble_size,
                                  reneel_ensemble_size=args.reneel_ensemble_size,
                                  rg_parameter=args.rg_parameter)
            run_reneel_and_collect_output(args.reneelpath, args.outputdir, reneelrun, args.keepresults, test_mode=args.test, n_cpu=args.nproc)
            print(f"{datetime.now():%m/%d/%Y %I:%M:%S %p} test = {args.test}\n",
                  reneelrun, file=logfile)