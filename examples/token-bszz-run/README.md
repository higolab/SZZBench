# A complete run: token-level B-SZZ over the shipped suite

This directory holds one run of B-SZZ on token-level histories over every scenario SZZBench ships,
with the predictions it made and the report SZZBench wrote. It is a companion of
[../pyszz-run/](../pyszz-run/README.md), whose B-SZZ it runs, and like it re-scores without the tool
installed.

- **Tool**: PySZZ's B-SZZ, as in [../pyszz-run/](../pyszz-run/README.md), run on copies of the
  generated repositories in which every `.java` file of every commit is rewritten to one token per
  line. The rewriting uses the modified cregit of the MV-SZZ replication package
  ([higolab/majority-voting-szz-replication-package](https://github.com/higolab/majority-voting-szz-replication-package)
  v1.1, `tools/cregit.zip`, GPL v3, not included here). It is run through
  `tools/adapters/token_bszz_to_predictions.py`, in the image built from `tools/adapters/token-bszz/`.
- **Suite**: 279 scenarios (133 classic, 146 graph)
- **Measured**: 2026-09-30 on macOS 26.3 (Apple silicon) with Docker Desktop (engine 29.8.1).
  - The image was `sha256:914fb8714622…`: Ubuntu 20.04 on amd64 under emulation, JDK 1.8.0_452,
    srcML 1.0.0, Exuberant Ctags 5.9, and BFG `1.12.16-SNAPSHOT (blobexec-fbf55a1)`.
  - B-SZZ ran on the host, as in `../pyszz-run/`: Python 3.14.7 with `PYTHONHASHSEED=0`,
    GitPython 3.1.7, PyDriller 1.15.2 and dateparser 0.7.6.

## Setting it up

1. Set up PySZZ as [../pyszz-run/README.md](../pyszz-run/README.md) describes. B-SZZ skips no comment
   lines, so it needs no srcML on the host.
2. Unpack the replication package's cregit:
   `unzip majority-voting-szz-replication-package/tools/cregit.zip`, which gives a `cregit`
   directory.
3. Build the image with Docker (about ten minutes under emulation on Apple silicon):

```bash
docker build --platform linux/amd64 -t szzbench-token-bszz tools/adapters/token-bszz
```

The Dockerfile is the replication package's `docker/cregit` image, rebuilt on images that are still
published:

- Its base image, `sbtscala/scala-sbt:8-jdk-focal`, is gone. This one starts from
  `eclipse-temurin:8-jdk-focal` and adds sbt.
- Its BFG fork is built with sbt 0.13.13, whose plugins moved from Bintray, which closed, to
  repo.scala-sbt.org.
- srcML 1.0.0's Ubuntu package exists for amd64 only, so the image is amd64 on every host.

cregit's own tools are not built at all. The one the rewrite needs, `srcml2token`, ships compiled
in `cregit.zip`.

The srcML package, sbt and the BFG fork are pinned to versions, but the base image and the apt
packages are not. `eclipse-temurin:8-jdk-focal` is a tag, which can move to another build or be
withdrawn, and apt installs what Ubuntu 20.04's archive holds at build time, ctags included. An
image built today may therefore differ from the one this run used (**Measured**, at the top).
Check its versions before comparing its runs with this one:

```bash
docker run --rm --platform linux/amd64 szzbench-token-bszz \
    sh -c 'java -version; srcml --version; ctags --version | head -n 1'
```

This run's image reported JDK 1.8.0_452, srcML 1.0.0 and Exuberant Ctags 5.9. ctags matters most
(see [What these numbers depend on](#what-these-numbers-depend-on)).

## The commands

```bash
szzbench generate-all-repos

python tools/adapters/token_bszz_to_predictions.py \
    --cregit-root /path/to/cregit \
    --pyszz-root /path/to/pyszz_v2-output-line-mapping-for-variants \
    --pyszz-python /path/to/python-with-pyszz-libraries \
    --generated-root generated-input-repos \
    --token-root results/token-bszz/repos \
    --out results/token-bszz/predictions.jsonl

szzbench evaluate \
    --predictions results/token-bszz/predictions.jsonl \
    --generated-root generated-input-repos \
    --include-generated \
    --out results/token-bszz
```

The adapter took about eight minutes. Rewriting the 279 repositories in the container took most of
that, and B-SZZ under a minute. `predictions.jsonl` here is `--out` as the adapter wrote it, and
`evaluation-results.md` is the report the evaluation wrote. Next to `--out`, `token-bszz-run.json`
records the image id, the window size and B-SZZ's environment.

In `--token-root`, `tokenization.json` records how the repositories there were tokenized: the
variant, the window size and the image id. `--skip-tokenize` runs B-SZZ on them again without
rewriting them. It refuses when `--variant` or `--window-size` differs from the record, or when
there is no record, as after a rewrite that stopped part way. `token-bszz-run.json` then reports
the recorded image.

## What the adapter does

1. **It rewrites each repository.** `tokenize-repos.sh` copies the repository and runs the BFG
   fork with `--blob-exec` of cregit's `tokenBySha.pl` on every `.java` blob, as the replication
   package's `run_cregit_1token.sh` does.
   - Each Java file becomes one srcML token per line (`name|locked`, `operator|!`), and every comment
     becomes the token `comment`.
   - Other files keep their lines. The seven Python scenarios, SZZ-0200 to SZZ-0206, are left
     unchanged, and their answers are exactly line-level B-SZZ's.
   - A rewrite that fails is that scenario's tool error. Its `tokenize.status` and `tokenize.log`
     say why, and the other repositories are still rewritten. Any other step that fails stops
     `tokenize-repos.sh`, and the adapter with it, with the failed command's message. Examples are
     an image with no BFG jar, or with more than one, and a copy of a repository that fails.
2. **It runs B-SZZ.** Each rewritten repository gets the original's metadata, with its commit map
   re-keyed to the rewritten hashes. Then `pyszz_variants_to_predictions.py --tools b-szz` runs on
   them.
3. **It maps the answers back.** BFG adds `Former-commit-id: <hash>` to every commit it rewrites,
   which is the footer cregit's `remapCommits` reads. Each answer is therefore named by the
   original repository's commit, and a commit BFG left alone keeps its hash. BFG rewrites what the
   refs reach, so a commit that no ref reaches has no rewritten copy and is left out of the map.
   These are the deleted branches of SZZG-0072 and SZZG-0122.

## What it scores

| | PASS | `control` | `discriminating` | TP | FP | FN | precision | recall |
|---|---|---|---|---|---|---|---|---|
| token-level B-SZZ | **164** | 153 / 233 | **11 / 46** | 217 | 41 | 124 | 0.841 | 0.636 |
| *B-SZZ* ([../pyszz-run/](../pyszz-run/README.md)) | 156 | 156 / 233 | 0 / 46 | 229 | 72 | 112 | 0.761 | 0.672 |
| *PyDriller 2.12* ([../pydriller-run/](../pydriller-run/README.md)) | 161 | 160 / 233 | 1 / 46 | 235 | 66 | 106 | 0.781 | 0.689 |
| *`position-1`* ([floor](../../docs/baselines.md)) | 160 | | | | | | | |

No scenario reported a tool error. Two runs from scratch gave the same answer on all 279
scenarios, from identical token-level histories.

## What tokens change

Against line-level B-SZZ, token-level B-SZZ gains 31 scenarios and loses 23. Three effects account
for the ones below, each checked on the repositories.

- **Tokens separate what one line merges.** A line whose tokens come from two commits blames to
  both. In SZZ-0136, `c1` writes `return value > min;` and `c2` extends the same line to
  `return value > min && value < max;`. Line-level blame answers `c2`; token-level blame answers
  `c1` and `c2`, the oracle. SZZG-0069, a rebase that splits the bug-inducing change in two, is
  answered the same way: `r2` at line level, `r1` and `r2` at token level. Token-level B-SZZ passes
  11 `discriminating` scenarios, where line-level B-SZZ
  passes none: SZZ-0136, SZZ-0192, SZZ-0197, SZZ-0212, SZZ-0215, SZZ-0219, SZZ-0225, SZZG-0028,
  SZZG-0069, SZZG-0076 and SZZG-0119.
- **Formatting changes no token.** SZZ-0081's `c2` reformats `Range.java`, which at line level is 9
  insertions and 3 deletions. In the token-level history, `c2` changes no file, so blame passes it
  and reaches `c1`. Line-level B-SZZ answers `c2`. The same holds for the whitespace-only
  re-indentation between the two faults of SZZ-0212. Intermediate noise, S3, accounts for 8 of the
  31 gains.
- **A fix that only inserts tokens leaves nothing to blame.** SZZ-0014's fix turns
  `return locked;` into `return !locked;`. At line level that is a modified line. At token level it
  inserts `operator|!` and deletes nothing, and B-SZZ blames only deleted lines.
  - Token-level B-SZZ therefore answers nothing in 63 scenarios, against line-level B-SZZ's 18.
    Each of the 45 extra scenarios is a fix that inserts tokens without deleting any.
  - This causes 14 of the 23 losses. Of the other nine:
    - five answer an extra commit, which in four of them is the initial commit;
    - three answer only one of two required commits;
    - one, SZZG-0049, answers the initial commit instead of the required one.
  - Two of the 45 pass: SZZG-0135 and SZZG-0136, whose correct answer is no commit. Token-level
    B-SZZ passes them without seeing why.

## What these numbers depend on

- **The window size.** It is one token per line (`--window-size 1`); the replication package
  prepares 1 to 15.
- **ctags.** `tokenizeSrcMl.pl` asks ctags for declarations with `--_xformat`, an option of
  Universal Ctags. This image, like the replication package's, installs Ubuntu 20.04's Exuberant
  Ctags, which rejects the option (`ctags: Unknown option: --_xformat`), so the tokens carry no
  declaration kinds. The Dockerfile does not pin the package, so check `ctags --version` in a
  rebuilt image, as [Setting it up](#setting-it-up) shows. Another ctags, a Universal Ctags in
  particular, can change the tokens.
- **BFG's parallelism.** The adapter runs BFG with one processor (`-XX:ActiveProcessorCount=1`).
  With several, a run over the suite once stopped for good, with two tokenizer processes waiting
  for their input. One processor rewrites the same history one blob at a time. A time limit with
  one retry guards against any other hang; this run needed neither.
- **BFG's working directory.** The fork opens the repository of its working directory while it
  parses `--blob-exec`, and outside one it fails with `None.get` yet exits 0. The adapter runs it
  from its own checkout, as the replication package's script does. It counts a run as done only
  when BFG reports that it rewrote the history, or that there was nothing to rewrite.
- **B-SZZ's environment**, as in [../pyszz-run/](../pyszz-run/README.md).

## Reproducing it

The generator is deterministic, so the hashes in `predictions.jsonl`, which are the original
repositories' hashes, match a fresh `generate-all-repos` on the same scenarios. `szzbench evaluate`
re-scores them without Docker, cregit or PySZZ. Re-running the adapter reproduces the predictions
themselves.

## What this is not

This is B-SZZ on 1-token histories, one of the representations the MV-SZZ replication package
prepares. It is not MV-SZZ, which votes across several representations.
