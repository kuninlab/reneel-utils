"""Snakemake module: build reneel, format edgelists for it, and run it.

Import from another workflow with

    module reneel:
        snakefile: github("kuninlab/reneel-utils", path="workflow/reneel.smk", tag="...")
        config: config["reneel"]
    use rule * from reneel

See the README for the config keys.
"""

# Fork of prameshsingh/generalized-modularity-density with the OpenMP thread-count fix
RENEEL_REPO = config.get("repo", "sekunder/generalized-modularity-density")
RENEEL_COMMIT = config.get("commit", "013f0db53d9b48b2bccdcc11e9724c28ba926873")

EXE = config.get("executable", "resources/reneel/reneel")
NET = config.get("network_dir", "data/processed/{dataset}")
RES = config.get("results_dir", "results/reneel/{dataset}")
EXT = config.get("ext", ".csv")
CONDA_ENV = config.get("conda_env", "envs/reneel.yaml")


def reneel_targets(networks, chi_replicates, seed_multiplier=1,
                   pattern=RES + "/partition_{networkname}_{seed}-{chi}" + EXT):
    """Partition files for every network, with n_replicates seeds per chi value.
    Seeds are seed_multiplier * i for i in range(n_replicates)."""
    return [pattern.format(**net, seed=seed_multiplier * i, chi=entry["chi"])
            for net in networks
            for entry in chi_replicates
            for i in range(entry["n_replicates"])]


rule reneel_build:
    output: EXE
    localrule: True  # needs network; cluster compute nodes often have none
    conda: CONDA_ENV
    params:
        url=f"https://github.com/{RENEEL_REPO}/archive/{RENEEL_COMMIT}.tar.gz",
    shell:
        # Recent conda-forge compilers put cc/clang/gcc on PATH without setting $CC,
        # so point at the env's OpenMP headers/libs explicitly.
        """
        prefix=$(python -c 'import sys; print(sys.prefix)')
        src=$(mktemp -d)
        trap 'rc=$?; rm -rf "$src"; exit $rc' EXIT
        curl -sSfL {params.url} | tar xz -C "$src" --strip-components=1
        ${{CC:-cc}} ${{CFLAGS:-}} -O2 -fopenmp \
            -I"$prefix/include" "$src"/main.c "$src"/help.c "$src"/rg.c \
            ${{LDFLAGS:-}} -L"$prefix/lib" -Wl,-rpath,"$prefix/lib" -lm \
            -o {output}
        """


rule reneel_format:
    input:
        NET + "/{networkname}" + EXT,
    output:
        NET + "/clean_{networkname}" + EXT,
        NET + "/key_{networkname}" + EXT,
        NET + "/info_{networkname}" + EXT,
        NET + "/degree_{networkname}" + EXT,
    wildcard_constraints:
        networkname=r"(?!(clean|key|info|degree)_)[^/]+",
    conda: CONDA_ENV
    params:
        args=config.get("format_args", ""),
    shell:
        "format_edgelist -i {input} {params.args}"


rule reneel_run:
    input:
        exe=EXE,
        original=NET + "/{networkname}" + EXT,
        clean=NET + "/clean_{networkname}" + EXT,
        info=NET + "/info_{networkname}" + EXT,
        degree=NET + "/degree_{networkname}" + EXT,
    output:
        partition=RES + "/partition_{networkname}_{seed}-{chi}" + EXT,
        results=RES + "/results_{networkname}_{seed}-{chi}" + EXT,
    log:
        RES + "/logs/{networkname}_{seed}-{chi}.log",
    wildcard_constraints:
        seed=r"\d+",
        chi=r"\d*\.?\d+",
    threads: config.get("threads", 1)
    conda: CONDA_ENV
    params:
        krg=config.get("krg", 2),
        rg_ensemble=config.get("rg_ensemble_size", 10),
        reneel_ensemble=config.get("reneel_ensemble_size", 10),
    shell:
        """
        run_reneel -i {input.original} -x {input.exe} \
            -c {wildcards.chi} -n 1 -s {wildcards.seed} -p {threads} \
            -g {params.krg} -e {params.rg_ensemble} -f {params.reneel_ensemble} \
            --partition-out {output.partition} --results-out {output.results} \
            -l {log}
        """


rule reneel_all:
    input:
        reneel_targets(config.get("networks", []),
                       config.get("chi_replicates", []),
                       config.get("seed_multiplier", 1)),
