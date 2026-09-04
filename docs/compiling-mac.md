# Compiling reneel on macOS

The [generalized-modularity-density README](https://github.com/prameshsingh/generalized-modularity-density)
says to compile with:

```bash
gcc-9 main.c help.c rg.c -fopenmp -lm
```

That doesn't work out of the box on macOS, and it's not obvious why from the error
messages alone. This doc explains the fix, and a real bug in the C code that the
fix exposes.

## Get the source

Upstream (`prameshsingh/generalized-modularity-density`) has a bug that segfaults
on macOS under normal use (see "Known bug" below). Clone the fork with the fix
instead, from the `fix-omp-thread-count` branch:

```bash
git clone --branch fix-omp-thread-count \
    https://github.com/sekunder/generalized-modularity-density.git
```

The fix is submitted upstream as
[prameshsingh/generalized-modularity-density#2](https://github.com/prameshsingh/generalized-modularity-density/pull/2).
If/when that merges, switch back to cloning upstream's `main`.

## Why the naive compile fails

On macOS, `/usr/bin/gcc` isn't GCC — it's a symlink into Apple's Clang (part of the
Xcode Command Line Tools). Apple's Clang doesn't ship OpenMP support: `-fopenmp`
is rejected outright, or if you work around that, `omp.h` isn't found and there's
no `libomp` to link against. There's also no `gcc-9` on macOS unless you've
separately installed one. Either way you hit a wall quickly if you're not already
familiar with the difference between "the `gcc` on your PATH" and "actual GCC."

## Prerequisites

Install a Clang build that *does* support OpenMP, plus the OpenMP runtime:

```bash
brew install llvm libomp
```

- `llvm` — Homebrew's full LLVM/Clang distribution (unlike Apple's stripped-down
  system Clang, this one supports `-fopenmp`).
- `libomp` — the OpenMP runtime library and headers (`omp.h`) that `-fopenmp`
  needs to compile and link against.

## Compile

From the `generalized-modularity-density` checkout:

```bash
LLVM_CLANG="$(brew --prefix llvm)/bin/clang"
LIBOMP="$(brew --prefix libomp)"

"$LLVM_CLANG" main.c help.c rg.c \
    -fopenmp -lm -O2 \
    -I"$LIBOMP/include" -L"$LIBOMP/lib" \
    -o reneel
```

You'll see a handful of `-Wformat`/`-Wformat-security` warnings (mismatched
`printf`/`fprintf` format specifiers, unrelated to OpenMP). These are pre-existing
issues in the C source and are harmless — safe to ignore.

Copy (or symlink) the resulting `reneel` binary wherever your workflow's config
expects it.

## Verify

```bash
otool -L reneel
```

You should see a dependency on `libomp.dylib` from your Homebrew prefix (e.g.
`/opt/homebrew/opt/libomp/lib/libomp.dylib`). This means `libomp` must stay
installed via Homebrew on any Mac that *runs* this binary — not just the one
that compiled it. It's a dynamic link, not a static one.

## ⚠️ Known bug: don't let the OpenMP thread count fall below the machine's core count

**Fixed** on the fork's `fix-omp-thread-count` branch (see "Get the source" above;
[upstream PR #2](https://github.com/prameshsingh/generalized-modularity-density/pull/2)).
If you're compiling from that branch, this section doesn't apply to you — it's
kept here as background, and as a warning for anyone still building from
unpatched upstream `main.c`.

`main.c` computes `size = omp_get_num_procs()` once at startup and uses it both
to size the `ensemble` array (`kmax = copy1 * size`) *and* as the assumed upper
bound for `omp_get_thread_num()` inside the `#pragma omp parallel` region that
fills that array. These two things are only guaranteed to agree if the actual
OpenMP runtime spawns exactly `size` threads for that parallel region.

If something constrains the runtime to fewer threads than `omp_get_num_procs()`
reports — most commonly, `OMP_NUM_THREADS` set below the machine's logical core
count — the parallel loop only fills in a fraction of the `ensemble` array.
Later code assumes the whole array is populated, walks into the uninitialized
slots, and segfaults. This reproduces reliably: on a 10-core machine, the exact
same invocation succeeds with `OMP_NUM_THREADS` unset and crashes 100% of the
time with e.g. `OMP_NUM_THREADS=2`.

On HPC systems this rarely bites, because job schedulers typically restrict CPU
*affinity* via cgroups — which `omp_get_num_procs()` itself respects — so the
array size and the actual thread count stay in sync automatically, without
anyone needing to set `OMP_NUM_THREADS`.

On a local Mac (no cgroup affinity control), the practical rule is: **don't set
`OMP_NUM_THREADS` (or anything else that caps OpenMP's thread count) below the
machine's logical CPU count when invoking `reneel`.** If you're driving this
from Snakemake, note that Snakemake auto-injects `OMP_NUM_THREADS` matching a
rule's resolved `threads:` — so a `--cores`/`-j` budget smaller than the
rule's `threads:` will silently cap the resolved thread count too, and trigger
this same crash. Always invoke Snakemake with at least as many cores as the
`reneel` rule requests.
