"""Tests of workflow/reneel.smk, driven through a throwaway project that imports it.

Needs a `snakemake` executable: $SNAKEMAKE if set, otherwise whatever is on PATH.
The e2e test also needs conda; run it with `pytest -m e2e`."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import DATA_DIR, KARATE_NODES

REPO = Path(__file__).resolve().parents[1]
SNAKEMAKE = os.environ.get("SNAKEMAKE") or shutil.which("snakemake")
pytestmark = pytest.mark.skipif(SNAKEMAKE is None, reason="snakemake not found (set $SNAKEMAKE)")

CHI_REPLICATES = [{"chi": 0.0, "n_replicates": 3}, {"chi": 0.1, "n_replicates": 1}]


def make_project(path, **config):
    """Project with karate at data/processed/toy/ and a Snakefile importing the module."""
    (path / "data/processed/toy").mkdir(parents=True)
    shutil.copy(DATA_DIR / "karate.txt", path / "data/processed/toy")
    config = {"ext": ".txt", "networks": [{"dataset": "toy", "networkname": "karate"}],
              "chi_replicates": CHI_REPLICATES, **config}
    (path / "Snakefile").write_text(f"""
module reneel:
    snakefile: {str(REPO / "workflow/reneel.smk")!r}
    config: {config!r}
use rule * from reneel
rule all:
    input: rules.reneel_all.input
    default_target: True
""")
    return path


def snakemake(project, *args):
    return subprocess.run([SNAKEMAKE, "-c", str(os.cpu_count()), *args],
                          cwd=project, capture_output=True, text=True)


def test_dry_run_targets(tmp_path):
    project = make_project(tmp_path, seed_multiplier=10)
    result = snakemake(project, "-n")
    assert result.returncode == 0, result.stderr
    out = result.stdout + result.stderr
    counts = dict(re.findall(r"^(reneel_\w+)\s+(\d+)$", out, flags=re.M))
    assert counts == {"reneel_build": "1", "reneel_format": "1", "reneel_run": "4"}
    partitions = set(re.findall(r"results/reneel/toy/partition_karate_[\d.-]+\.txt", out))
    assert partitions == {f"results/reneel/toy/partition_karate_{s}-{c}.txt"
                          for s, c in [(0, 0.0), (10, 0.0), (20, 0.0), (0, 0.1)]}


@pytest.mark.e2e
def test_build_and_run_with_conda(tmp_path):
    # Same env as the module ships, but installing reneelutil from this checkout instead of GitHub
    env = (REPO / "workflow/envs/reneel.yaml").read_text()
    env = re.sub(r"- git\+https://github.com/kuninlab/reneel-utils@\S+", f"- {REPO}", env)
    env_file = tmp_path / "reneel-local.yaml"
    env_file.write_text(env)

    # chi = 0.0 only: real reneel does not terminate on karate for chi > 0
    project = make_project(tmp_path / "project", conda_env=str(env_file), threads=2,
                           chi_replicates=[{"chi": 0.0, "n_replicates": 3}])
    result = snakemake(project, "--sdm", "conda")
    assert result.returncode == 0, result.stdout + result.stderr

    assert os.access(project / "resources/reneel/reneel", os.X_OK)
    for s, c in [(0, 0.0), (1, 0.0), (2, 0.0)]:
        partition = project / f"results/reneel/toy/partition_karate_{s}-{c}.txt"
        assert len(partition.read_text().split()) == KARATE_NODES
        assert (project / f"results/reneel/toy/results_karate_{s}-{c}.txt").exists()
