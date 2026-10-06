import shutil
import subprocess
import threading

import pytest

from conftest import KARATE_NODES, fake_reneel_calls
from reneelutil import run_reneel
from reneelutil.run_reneel import plan_runs


# ---- plan_runs ----

def test_plan_runs_single_nruns_applies_to_every_chi():
    runs = plan_runs(["a"], [0.0, 0.1], 3, seeds=[7])
    assert [(f, c) for f, c, _ in runs] == [("a", 0.0)] * 3 + [("a", 0.1)] * 3


def test_plan_runs_nruns_per_chi():
    runs = plan_runs(["a", "b"], [0.0, 0.1, 0.2], [2, 1, 0], seeds=[7])
    assert [(f, c) for f, c, _ in runs] == [("a", 0.0), ("a", 0.0), ("b", 0.0), ("b", 0.0),
                                            ("a", 0.1), ("b", 0.1)]


def test_plan_runs_one_element_list_same_as_int():
    assert plan_runs(["a"], [0.0, 0.1], [2], seeds=[1]) == plan_runs(["a"], [0.0, 0.1], 2, seeds=[1])


def test_plan_runs_length_mismatch():
    with pytest.raises(ValueError):
        plan_runs(["a"], [0.0, 0.1, 0.2], [1, 2])


def test_plan_runs_cycles_seeds():
    runs = plan_runs(["a"], [0.0], 5, seeds=[1, 2])
    assert [s for _, _, s in runs] == [1, 2, 1, 2, 1]


def test_plan_runs_random_seeds_when_none_given():
    seeds = [s for _, _, s in plan_runs(["a"], [0.0], 4)]
    assert len(seeds) == 4 and all(isinstance(s, int) for s in seeds)


# ---- running (with the fake executable) ----

def run(*args):
    """Call run_reneel.main, returning the exit code (0 if it returned normally)."""
    try:
        run_reneel.main([str(a) for a in args])
    except SystemExit as e:
        return e.code
    return 0


def test_explicit_output_paths(formatted_karate, fake_reneel, tmp_path):
    part = tmp_path / "out" / "partition_karate_3-0.1.txt"
    res = tmp_path / "out" / "results_karate_3-0.1.txt"
    code = run("-i", formatted_karate, "-x", fake_reneel, "-c", 0.1, "-n", 1, "-s", 3, "-p", 1,
               "--partition-out", part, "--results-out", res, "-l", tmp_path / "run.log")
    assert code == 0
    assert len(part.read_text().splitlines()) == KARATE_NODES
    assert res.read_text().split() == ["3", "0.1"]
    # nothing but the outputs in the output directory (temp work dir cleaned up)
    assert sorted(p.name for p in part.parent.iterdir()) == sorted([part.name, res.name])


def test_input_directory_left_untouched(formatted_karate, fake_reneel, tmp_path):
    before = sorted(p.name for p in formatted_karate.parent.iterdir())
    code = run("-i", formatted_karate, "-x", fake_reneel, "-n", 2, "-s", 1, 2, "-k",
               "-o", tmp_path / "out", "-l", tmp_path / "run.log")
    assert code == 0
    assert sorted(p.name for p in formatted_karate.parent.iterdir()) == before
    # reneel ran somewhere other than the input directory
    assert all(not line.startswith(str(formatted_karate.parent) + " ")
               for line in fake_reneel_calls(tmp_path))


def test_default_naming_has_seed_chi_and_id(formatted_karate, fake_reneel, tmp_path):
    out = tmp_path / "out"
    run("-i", formatted_karate, "-x", fake_reneel, "-c", 0.05, "-n", 1, "-s", 9, "-k",
        "-o", out, "-l", tmp_path / "run.log")
    names = sorted(p.name for p in out.iterdir())
    assert len(names) == 2
    assert names[0].startswith("partition_karate_9-0.05-") and names[0].endswith(".txt")
    assert names[1].startswith("results_karate_9-0.05-")


def test_concurrent_runs_on_same_input(formatted_karate, fake_reneel, tmp_path):
    out = tmp_path / "out"
    codes = {}

    def go(seed):
        codes[seed] = run("-i", formatted_karate, "-x", fake_reneel, "-n", 1, "-s", seed, "-p", 1,
                          "--partition-out", out / f"partition_karate_{seed}-0.0.txt",
                          "--results-out", out / f"results_karate_{seed}-0.0.txt",
                          "-l", tmp_path / f"run{seed}.log")

    threads = [threading.Thread(target=go, args=(s,)) for s in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert codes == {s: 0 for s in range(4)}
    for s in range(4):
        assert (out / f"results_karate_{s}-0.0.txt").read_text().split() == [str(s), "0.0"]
    assert len({line.split()[0] for line in fake_reneel_calls(tmp_path)}) == 4  # 4 distinct work dirs


def test_failure_exits_nonzero_and_batch_continues(formatted_karate, fake_reneel, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_RENEEL_FAIL", "2")
    out = tmp_path / "out"
    code = run("-i", formatted_karate, "-x", fake_reneel, "-n", 3, "-s", 1, 2, 3,
               "-o", out, "-l", tmp_path / "run.log")
    assert code == 1
    assert len(fake_reneel_calls(tmp_path)) == 3
    partitions = sorted(p.name for p in out.iterdir())
    assert len(partitions) == 2
    assert not any(name.startswith("partition_karate_2-") for name in partitions)


def test_toml_nruns_per_chi(formatted_karate, fake_reneel, tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(f"""
[run_reneel]
input = ["{formatted_karate}"]
chi = [0.0, 0.1]
nruns = [2, 1]
seed = [5]
reneelpath = "{fake_reneel}"
output = "{tmp_path / 'out'}"
logfile = "{tmp_path / 'run.log'}"
nproc = 1
""")
    assert run("--config", config) == 0
    names = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert sum(n.startswith("partition_karate_5-0.0-") for n in names) == 2
    assert sum(n.startswith("partition_karate_5-0.1-") for n in names) == 1


def test_explicit_outputs_need_exactly_one_run(formatted_karate, fake_reneel, tmp_path):
    code = run("-i", formatted_karate, "-x", fake_reneel, "-n", 2,
               "--partition-out", tmp_path / "p.txt", "-l", tmp_path / "run.log")
    assert code == 2  # argparse error
    assert fake_reneel_calls(tmp_path) == []


def test_bad_nruns_length_is_argparse_error(formatted_karate, fake_reneel, tmp_path):
    code = run("-i", formatted_karate, "-x", fake_reneel, "-c", 0.0, 0.1, 0.2, "-n", 1, 2,
               "-l", tmp_path / "run.log")
    assert code == 2


def test_test_mode_runs_echo(formatted_karate, tmp_path):
    out = tmp_path / "out"
    code = run("-i", formatted_karate, "-x", "/nonexistent/reneel", "--test", "-n", 1, "-s", 4,
               "-o", out, "-l", tmp_path / "run.log")
    assert code == 0
    (part,) = out.iterdir()
    assert part.read_text().split() == ["Testing", "4", "0.0"]


@pytest.mark.skipif(shutil.which("run_reneel") is None, reason="package not installed")
def test_entry_point_installed():
    result = subprocess.run(["run_reneel", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--partition-out" in result.stdout
