import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

from reneelutil import format_edgelist

DATA_DIR = Path(__file__).parent / "data"
KARATE_NODES = 34
KARATE_EDGES = 78

# Stand-in for the reneel executable. Same argument order and file conventions:
# reads clean_/degree_/info_<name> from its cwd, writes partition_/results_<name> there.
# FAKE_RENEEL_LOG: append "cwd argv..." per call. FAKE_RENEEL_FAIL: "all" or a seed to fail on.
FAKE_RENEEL = '''#!{python}
import os, sys
from pathlib import Path
krg, rg, ren, seed, chi, name = sys.argv[1:7]
for prefix in ("clean_", "degree_", "info_"):
    if not Path(prefix + name).exists():
        sys.exit(f"missing {{prefix}}{{name}} in {{os.getcwd()}}")
if "FAKE_RENEEL_LOG" in os.environ:
    with open(os.environ["FAKE_RENEEL_LOG"], "a") as log:
        print(os.getcwd(), *sys.argv[1:], file=log)
if os.environ.get("FAKE_RENEEL_FAIL") in ("all", seed):
    sys.exit(1)
n_nodes = int(Path("info_" + name).read_text().split()[0])
Path("partition_" + name).write_text("".join(f"{{i % 2 + 1}}\\n" for i in range(n_nodes)))
Path("results_" + name).write_text(f"{{seed}} {{chi}}\\n")
'''


@pytest.fixture
def fake_reneel(tmp_path, monkeypatch):
    """Path to a fake reneel executable; its calls are logged to `fake_reneel.log`."""
    exe = tmp_path / "bin" / "reneel"
    exe.parent.mkdir()
    exe.write_text(FAKE_RENEEL.format(python=sys.executable))
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("FAKE_RENEEL_LOG", str(tmp_path / "fake_reneel.log"))
    monkeypatch.delenv("FAKE_RENEEL_FAIL", raising=False)
    return exe


def fake_reneel_calls(tmp_path):
    log = tmp_path / "fake_reneel.log"
    return log.read_text().splitlines() if log.exists() else []


@pytest.fixture
def karate(tmp_path):
    """Unformatted copy of the karate edgelist in its own directory."""
    net_dir = tmp_path / "net"
    net_dir.mkdir()
    return Path(shutil.copy(DATA_DIR / "karate.txt", net_dir))


@pytest.fixture
def formatted_karate(karate):
    """Karate edgelist with clean_/key_/info_/degree_ files next to it."""
    format_edgelist.main(["-i", str(karate)])
    return karate
