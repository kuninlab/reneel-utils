from conftest import KARATE_EDGES, KARATE_NODES


def test_outputs_exist(formatted_karate):
    for prefix in ["clean_", "key_", "info_", "degree_"]:
        assert formatted_karate.with_stem(prefix + formatted_karate.stem).exists()


def test_info_counts(formatted_karate):
    info = formatted_karate.with_stem("info_karate").read_text().split()
    assert [int(x) for x in info] == [KARATE_NODES, KARATE_EDGES]


def test_nodes_renumbered_1_to_n(formatted_karate):
    nodes = set()
    for line in formatted_karate.with_stem("clean_karate").read_text().splitlines():
        u, v, _ = line.split()
        nodes.update([int(u), int(v)])
    assert nodes == set(range(1, KARATE_NODES + 1))


def test_key_and_degree_have_one_line_per_node(formatted_karate):
    for prefix in ["key_", "degree_"]:
        lines = formatted_karate.with_stem(prefix + "karate").read_text().splitlines()
        assert len(lines) == KARATE_NODES
