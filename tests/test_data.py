import pytest

from reneelutil.data import get_available_clustering, load_partition


@pytest.fixture
def clustering_dir(tmp_path):
    d = tmp_path / "clustering"
    d.mkdir()
    (d / "key_mb_net.csv").write_text("101\n102\n103\n")
    for name in ["partition_mb_net_7-0.05-a1b2c3d4.csv",  # run_reneel default naming
                 "partition_mb_net_8-0.1.csv",            # Snakemake naming (no id)
                 "partition_notes.txt"]:                  # doesn't match the pattern
        (d / name).write_text("1\n1\n2\n")
    return d


@pytest.mark.parametrize("name,seed,chi", [("partition_mb_net_7-0.05-a1b2c3d4.csv", 7, 0.05),
                                           ("partition_mb_net_8-0.1.csv", 8, 0.1)])
def test_load_partition(clustering_dir, name, seed, chi):
    df = load_partition(clustering_dir / "key_mb_net.csv", clustering_dir / name, include_seed=True)
    assert list(df.index) == [101, 102, 103]
    assert list(df.columns) == [(chi, seed)]
    assert list(df[(chi, seed)]) == [1, 1, 2]


def test_load_partition_name_mismatch(clustering_dir):
    (clustering_dir / "key_other.csv").write_text("1\n")
    with pytest.raises(AssertionError):
        load_partition(clustering_dir / "key_other.csv", clustering_dir / "partition_mb_net_8-0.1.csv")


def test_get_available_clustering_skips_nonmatching(clustering_dir):
    df = get_available_clustering(clustering_dir)
    assert sorted(zip(df["seed"], df["chi"], df["id"].fillna(""))) == [(7, 0.05, "a1b2c3d4"), (8, 0.1, "")]
    assert set(df["name"]) == {"mb_net"}
