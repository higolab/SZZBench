# A complete run: five PySZZ variants over the shipped suite

This directory holds one run of five SZZ variants over every scenario SZZBench ships, with the
commands that produced it, the predictions each variant made and the report SZZBench wrote for
each. It is the companion of [../pydriller-run/](../pydriller-run/README.md): a reader can see
what the variants do on the same suite, and re-score them without installing anything.

- **Tool**: B-SZZ, AG-SZZ, MA-SZZ, L-SZZ and R-SZZ as PySZZ v2 implements them, in the version
  the MV-SZZ replication package ships
  ([higolab/majority-voting-szz-replication-package](https://github.com/higolab/majority-voting-szz-replication-package)
  v1.1, `tools/pyszz_v2-output-line-mapping-for-variants.zip`), through
  `tools/adapters/pyszz_variants_to_predictions.py`. That PySZZ is licensed under the GPL v3 and
  is not included here.
- **Suite**: 279 scenarios (133 classic, 146 graph)
- **Measured**: 2026-09-30 on macOS 26.3 (Apple silicon), Python 3.14.7 with
  `PYTHONHASHSEED=0`, Git 2.50.1, srcML 1.0.0, and the versions of the libraries these variants
  import that PySZZ's `requirements.txt` pins: GitPython 3.1.7, PyDriller 1.15.2, dateparser 0.7.6

## Setting up PySZZ

The adapter runs PySZZ in-process, so it needs a Python with the libraries PySZZ imports. These
five variants import three of those in PySZZ's `requirements.txt`; the adapter itself needs
PyYAML.

```bash
git clone --branch v1.1 --depth 1 https://github.com/higolab/majority-voting-szz-replication-package.git
unzip majority-voting-szz-replication-package/tools/pyszz_v2-output-line-mapping-for-variants.zip
python -m pip install PyYAML GitPython==3.1.7 PyDriller==1.15.2 dateparser==0.7.6
```

AG-SZZ, MA-SZZ, L-SZZ and R-SZZ skip comment lines, and PySZZ finds the comments of a Java file
with srcML: `srcml` must be on `PATH`, and the adapter refuses to run those four without it.
PySZZ's own Docker image installs srcML 1.0.0 from a Debian package. The 1.0.0 packages for macOS
on srcML's release page are built for Intel; on Apple silicon they run under Rosetta 2 and need
not be installed. Unpack one and put a wrapper named `srcml` on `PATH`:

```bash
curl -LO https://github.com/srcML/srcML/releases/download/v1.0.0/srcml-1.0.0-macOS-10.15.2.pkg
pkgutil --expand-full srcml-1.0.0-macOS-10.15.2.pkg srcml-1.0.0
```

```sh
#!/bin/sh
SRCML=/path/to/srcml-1.0.0/srcml-1.0.0-macOS-10.15.2-SRCML.pkg/Payload/usr/local
DYLD_LIBRARY_PATH="$SRCML/lib" exec "$SRCML/bin/srcml" "$@"
```

## The commands

```bash
szzbench generate-all-repos

python tools/adapters/pyszz_variants_to_predictions.py \
    --tool-root /path/to/pyszz_v2-output-line-mapping-for-variants \
    --generated-root generated-input-repos \
    --output-root results/pyszz

for tool in b-szz ag-szz ma-szz l-szz r-szz; do
    szzbench evaluate \
        --predictions results/pyszz/$tool/$tool-predictions.jsonl \
        --generated-root generated-input-repos \
        --include-generated \
        --out results/pyszz/$tool
done
```

The adapter took about seven minutes for the five variants. PySZZ copies each repository into
`_szztemp/` under the current directory before it blames anything. The adapter runs Git isolated
from the caller's configuration, as SZZBench's generator does, and runs PySZZ with Python's hash
seed fixed to 0 unless `PYTHONHASHSEED` is set, for the reason below. `<variant>/predictions.jsonl`
here is the adapter's `results/pyszz/<variant>/<variant>-predictions.jsonl` with the `raw_file`
path and the repeated `scenario_id` removed from every prediction, and
`<variant>/evaluation-results.md` is the report the evaluation wrote.

## What it scores

| | PASS | `control` | `discriminating` | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|---|
| B-SZZ | **156** | 156 / 233 | 0 / 46 | 229 | 72 | 112 | 0.761 | 0.672 |
| AG-SZZ | **161** | 160 / 233 | 1 / 46 | 234 | 66 | 107 | 0.780 | 0.686 |
| MA-SZZ | **161** | 160 / 233 | 1 / 46 | 234 | 65 | 107 | 0.783 | 0.686 |
| L-SZZ | **153** | 153 / 233 | 0 / 46 | 204 | 61 | 137 | 0.770 | 0.598 |
| R-SZZ | **156** | 156 / 233 | 0 / 46 | 216 | 49 | 125 | 0.815 | 0.633 |
| *PyDriller 2.12* ([../pydriller-run/](../pydriller-run/README.md)) | 161 | 160 / 233 | 1 / 46 | 235 | 66 | 106 | 0.781 | 0.689 |

No run reported a tool error, and every variant wrote a record for all 279 scenarios. L-SZZ's row
holds for this hash seed: under another it passes between 152 and 155 (see below).

Against [the cheap-rule floor](../../docs/baselines.md) — `position-1`, which opens no file, solves
160 and `blame-deleted-lines` 156 — the scoreboard says the five are one family, between 153 and
161, around a rule that opens no file. The sets say more.

## How the variants differ

All five pass the same 145 scenarios; 25 more are passed by some and not all, and 109 by none.
Each step from one variant to the next is visible as a handful of named scenarios:

- **B-SZZ is `blame-deleted-lines` with two differences.** Both pass 156 and share 155. B-SZZ
  gains SZZG-0002 because, for a file the fix renames, PySZZ blames the old path; it loses
  SZZG-0046 because that scenario's bug-fixing commit is a merge, for which PyDriller 1.15.2
  reports no modified files (measured: `merge` true, two parents, zero modifications), so PySZZ
  has nothing to blame. Against PyDriller 2.12, which also blames the old path and also skips a
  merge fix, B-SZZ shares 155 of its 161: the difference is `git blame -w`, which PyDriller uses and
  B-SZZ does not.
- **AG-SZZ blames with `-w` and skips comment lines.** It adds five scenarios to B-SZZ — SZZ-0083,
  SZZ-0100, SZZ-0108, SZZ-0212 and SZZG-0081, whitespace-only and formatting rewrites that `-w`
  carries the blame across — and loses none. SZZ-0212, a whitespace-only re-indentation between
  two faults, is the one `discriminating` scenario AG-SZZ and MA-SZZ pass, as PyDriller does.
- **MA-SZZ adds move detection (`-M`, `-C`) and sets meta-changes aside.** Against AG-SZZ it gains
  SZZ-0128 (extract helper after BIC) and SZZG-0005 (method move between classes), where AG-SZZ
  answers the commit that moved the code and MA-SZZ the one that introduced the fault. It loses
  SZZG-0045, whose bug-inducing commit *is* a merge: MA-SZZ counts merge commits among the
  meta-changes it blames past, and answers `c0`. It also loses SZZ-0155 (same bug introduced
  independently), answering one of its two required commits.
- **L-SZZ and R-SZZ keep one candidate of MA-SZZ's.** L-SZZ keeps the largest, R-SZZ the most
  recent. Both therefore fail all ten multi-commit oracles MA-SZZ passes (SZZ-0134, SZZ-0137,
  SZZ-0142, SZZ-0154, SZZ-0212, SZZG-0034, SZZG-0037, SZZG-0039, SZZG-0141, and SZZG-0138, which
  needs two of three): one commit cannot satisfy them. Where MA-SZZ's second candidate was a false
  positive the choice can win it back, and the two rules win back different scenarios: L-SZZ
  SZZ-0186 (under this hash seed, below) and SZZG-0109; R-SZZ SZZ-0121, SZZ-0187, SZZ-0188,
  SZZG-0001 and SZZG-0016. In the
  first four of R-SZZ's the other candidate is the initial commit, which is larger, so L-SZZ keeps
  the wrong one.

## What these numbers depend on

Four things about the environment change these results, and the adapter now says so, or fixes
them, instead of producing a different number quietly.

- **Python's hash seed (L-SZZ).** L-SZZ keeps the first of equally large candidates in the order
  it iterates a set of GitPython commits, and that order follows Python's per-process hash seed.
  Fifteen scenarios give it two equally large candidates, so its answer there changes from run to
  run. In twelve the verdict does not change: ten have a multi-commit oracle that one commit fails
  whichever it keeps, and in SZZG-0033 and SZZG-0139, whose `partial_credit` oracle needs one of two
  commits, either candidate is accepted. In SZZ-0183, SZZ-0186 and SZZG-0016 one candidate is the
  answer and the other is not, so L-SZZ passes between 152 and 155 depending on the seed; under
  seed 0 it keeps the answer only in SZZ-0186. R-SZZ, which keeps the latest committer date, has
  no tie on the suite: no two commits of a repository share one.
- **srcML.** Without it, PySZZ logs an error each time it looks for the comments of a Java file and
  keeps the comment lines, and AG-, MA-, L- and R-SZZ are no longer the variants they are named
  after. The adapter refuses to run them when `srcml` is not on `PATH`.
- **GitPython 3.1.7.** GitPython releases after it refuse `git blame --ignore-revs-file` as an
  unsafe option, and MA-, L- and R-SZZ use it to set meta-changes aside. With GitPython 3.1.62 the
  blame raised on SZZ-0216, SZZG-0007 and SZZG-0045; PySZZ caught the exception, logged it and
  carried on, so the scenario looked answered — by nothing on SZZ-0216 and SZZG-0045. The adapter
  now fails a scenario on which PySZZ logged an exception as a tool error (`status: error`), and
  warns at start-up when GitPython refuses the option.
- **PyDriller 1.15.2 and dateparser.** The adapter used to stand in for both with its own
  approximation. It is not PyDriller. Its line counts give a root commit no lines, so in the 29
  scenarios where PyDriller finds the initial commit the largest candidate, L-SZZ kept another;
  and it diffed a merge fix against its first parent, where PyDriller 1.15.2 reports no modified
  files (SZZG-0046, every variant). Measured with the same hash seed, those are all the
  differences. The adapter now requires the pinned libraries, and uses the approximation only
  with `--compat-layer`, for a smoke test.

What PySZZ logs at error level as part of its normal behaviour is kept, not failed: a file its
comment parsers do not handle keeps its comment lines, as it does in PySZZ's own environment. In
this run that is `range-limits.properties` and `retry.properties`; the adapter's raw output lists
it per scenario under `pyszz_logged`.

## Configuration

The adapter calls each variant as PySZZ's `main.py` does with PySZZ's `conf/*.yml`: no issue-date
filter; `max_change_size` 20 for AG-, MA-, L- and R-SZZ; `detect_move_from_other_files: 1`
(`git blame -C`) for MA-, L- and R-SZZ, which blame with `-M` by default; only deleted lines; no
revert filter. Each bug-fixing commit is analysed on its own.

One setting differs on purpose: PySZZ's `conf/rszz.yml` limits R-SZZ to `.java` files, and the
adapter restricts no variant by file extension, so all five read the same files.

## Reproducing it

The generator is deterministic, so the hashes in the `predictions.jsonl` files match a fresh
`generate-all-repos` on the same scenarios, and `szzbench evaluate` re-scores them without PySZZ,
srcML or the pinned libraries. Re-running the adapter reproduces the predictions themselves. A
scenario edited after this run changes its hashes, and its record here then no longer matches;
the suite size and date at the top of this file say what the run was measured on.

## What this is not

These are PySZZ's implementations of five variants, run with one configuration. L-SZZ and R-SZZ are
the *largest* and *most recent* candidate selections of da Costa et al.; R-SZZ is not the
refactoring-aware RA-SZZ. None of the five uses issue dates, which PySZZ can filter on and
SZZBench's scenarios do not provide.
