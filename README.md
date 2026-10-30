# SZZBench

SZZBench is a tool for generating and verifying synthetic Git repositories for evaluating SZZ techniques.

In SZZ, a tool starts from a commit that fixes a bug, traces the history backward, and estimates the commit that likely introduced the bug. SZZBench provides a basis for checking, with small controlled Git repositories, what kinds of histories make this estimation work well and what kinds of histories make it fail.

## Quickstart

From a clean clone to an evaluation report. The last command re-scores a recorded run of a
third-party SZZ implementation, so it also says whether this installation agrees with ours. The
activation line is for macOS and Linux; see [Installation](#installation) for Windows.

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
szzbench generate-all-repos
szzbench evaluate \
    --predictions examples/pydriller-run/predictions.jsonl \
    --generated-root generated-input-repos \
    --include-generated \
    --out results/pydriller
```

`generate-all-repos` writes 279 repositories under `generated-input-repos/` and takes about three
minutes; everything after it takes seconds. The evaluation prints `PASS: 161`, `FAIL: 118`,
precision 0.781 and recall 0.689.
[examples/pydriller-run/README.md](examples/pydriller-run/README.md) says what that run was, how it
was produced, and what the numbers mean — including why the tool passes 68.7 % of the `control`
scenarios and 2.2 % of the `discriminating` ones.

Two more commands are worth knowing before the rest of this file:

```bash
szzbench baselines --out results/floor
szzbench coverage --out results/coverage
```

The first scores rules that do no analysis at all, which is the floor any result on SZZBench should
be read against; the second reports what each scenario contributes. To evaluate your own tool,
produce the same JSONL and pass it to `szzbench evaluate`; the format is under [evaluate](#evaluate).

## Terminology

| Term | Meaning |
|---|---|
| SZZ | A family of techniques for estimating bug-inducing commits from bug-fixing commits. The name comes from Śliwerski, Zimmermann, and Zeller. |
| BFC | Bug-Fixing Commit. A commit that fixes a bug. |
| BIC | Bug-Inducing Commit. A commit that introduces a bug. |
| oracle | Ground-truth information. It describes which commits are BICs / BFCs and which lines or entities correspond to faults / fixes. |
| scenario | A file that describes a synthetic history. Normal scenarios use `scenario.yml`; complex scenarios use `scenario.graph.yml`. |

## Two types of scenarios in SZZBench

SZZBench has two main types of scenarios.

### 1. Normal scenarios: `SZZ-XXXX`

Normal scenarios handle relatively simple histories.

```text
scenarios/
└── SZZ-0006/
    ├── scenario.yml
    └── README.md
```

They mainly assume the following:

- linear histories
- a single branch
- operations mainly based on `write_file` / `replace`
- one BFC per bug, with one or more BICs when the oracle is still an exact commit set
- small and readable synthetic histories

For normal scenarios, use the following commands:

```bash
szzbench validate
szzbench generate
szzbench verify
szzbench new-scenario
```

### 2. Graph scenarios: `SZZG-XXXX`

Graph scenarios handle complex histories that are difficult to represent with the normal `scenario.yml`.

```text
advanced-scenarios/
└── SZZG-0001/
    ├── scenario.graph.yml
    └── README.md
```

They mainly assume the following:

- branch / merge
- cherry-pick / backport
- rename / move / copy / delete
- multiple BFCs or multiple independent bugs
- direct BIC / origin BIC / contributing BIC
- work item / issue / developer hint
- evaluation policies such as top-k and relaxed evaluation

The keys a `scenario.graph.yml` may have are listed in [docs/graph-schema.md](docs/graph-schema.md); `validate-graph` warns about any other (`GW004`), except `notes` and keys that begin with `x-`, which are free notes.

For Graph scenarios, use the following commands:

```bash
szzbench validate-graph
szzbench generate-graph
szzbench verify-graph
szzbench new-graph-scenario
```

`scenario.graph.yml` is more expressive than the normal `scenario.yml`. Its schema is no longer a draft: it is versioned `graph-1.0`, and `docs/decisions/vocabulary.md` §4 records the bar it was measured against. A graph scenario declares `schema_version: "graph-1.0"` and a classic one `schema_version: "1.0"`, quoted; `validate-graph` and `validate` reject any other value (GE002, E004, E010).

### Scenario schema boundary policy

Use `scenario.yml` for the constrained subset of scenarios that can be represented as a linear `main` history with simple file operations and a simple commit-level exact-set oracle.

In practice, `scenario.yml` is appropriate when all of the following are true:

- the history is a single linear chain on `main`
- commit parents are implicit, or each commit depends only on the previous commit
- operations are limited to `write_file` and `replace`
- a commit may contain multiple operations
- a bug may have multiple BICs, as long as the expected answer is still a commit-level exact set
- each bug has one BFC

Use `scenario.graph.yml` when the scenario needs graph-specific history, relation metadata, special operations, or advanced evaluation semantics. This includes:

- explicit DAG history, branches, merge commits, squash merges, release branches, cherry-picks, or backports
- operations outside the normal subset, such as rename, move, copy, delete, binary writes, chmod, generated-file operations, entity moves/copies, commit generators, or patch-from/squash operations
- work items, issues, developer hints, clone/copy relationships, bug instances, origin faults, direct/origin BIC relationships, or refactoring metadata
- multiple BFCs or multiple independent bugs as the main evaluation unit
- evaluation variants, top-k evaluation, partial or relaxed credit, acceptable related commits, related-but-not-correct commits, or line/entity/branch/work-item/bug-level evaluation policies

In short, `scenario.yml` is treated as a restricted subset of `scenario.graph.yml`: linear `main` history plus a simple commit-level exact-set oracle. Anything that needs graph structure or richer evaluation metadata stays in `scenario.graph.yml`.

### What the benchmark does not test

`szzbench baselines` scores a declared family of naive predictors — metadata
only, history position only, file-touch shape, and the classic blame baseline —
with the ordinary evaluator, so every result on SZZBench can be read against a
floor. Measured on the shipped suite of 279 scenarios: **"report the second
commit of the history", which opens no file at all, solves 160/279 — four more
than the classic `blame-deleted-lines` baseline at 156/279**, and the lead has
changed hands with every batch of new scenarios. Some naive rule solves 233 of
the 279 scenarios, an oracle-aware upper bound rather than an attacker's score;
the forty-six it does not reach all have a multi-commit oracle, which is
forced rather than chosen: a one-commit answer is always named by one of the
positional rules, and an empty one by `abstain`. The metadata
family is at chance, which is the leakage guarantee below holding.

Every scenario declares `meta.tier`: **233 are `control`** — they check that a
method handles a specific input condition, and a naive rule may well solve them
— and **46 are `discriminating`**, which no declared naive baseline solves.
Thirty-four of those were designed against one axis: the answer is two commits,
and the fix's deleted lines do not blame to one of them. Five more fail the naive
rules differently — SZZ-0218's and SZZ-0220's answers are entirely reachable by
blame, which also hands over commits that are not answers; SZZ-0222's blame
answer contains no required commit at all; and SZZG-0148 and SZZG-0149 name
three commits under a credit threshold of two. The remaining seven were not
designed for the tier: they are older scenarios that turned out to resist every
naive rule. Every one of the seventeen categories has at least two, so a method
cannot pass a category by overfitting to a single history. A control that a
naive rule solves is not a defect; what the tier prevents is reading a
control as evidence that a method discriminates.

`szzbench coverage` is the companion command: it measures each scenario's
oracle size, the depth of its bug-introducing commit, how many distractors
touch the fault file, the size and branchiness of its history, and what plain
blame does with its oracle (`blame_class`), then groups the scenarios that
agree on the shape dimensions — and reports how many scenarios share each
declared fault statement, overall and per category (issue #13).

Read [docs/baselines.md](docs/baselines.md) before reporting or comparing
numbers on this benchmark. Raising that floor is tracked in issues #13, #14
and #35.

### What the generated repositories do not reveal

A tool is given a generated repository and the bug-fixing commit. Nothing inside
that repository identifies a commit's role in the oracle: commit messages
describe the change from the author's point of view and never carry a scenario
id, a role word or an operation list; authors and dates are derived from the
scenario id and the commit index, never from the role; and no file content or
path states which commit is the answer. Bug-fixing commits keep natural fix
wording, because the BFC is an input to SZZ rather than part of the answer.

Nor is the bug-fixing commit always in the history of HEAD. `generate` leaves
the default branch checked out, but `generate-graph` leaves HEAD on the branch
of the scenario's last commit, which may be another branch than the default
one: SZZG-0054 ends on `release`, and its only bug-fixing commit, on `main`, is
not reachable from HEAD. A bug-fixing commit may also stay on a branch that is
never merged, as in SZZG-0075. A tool should therefore start from the
bug-fixing commit it is given, or walk every ref (`git log --all`), not walk
history from HEAD. `metadata/graph-map.json` records where HEAD is (`head`);
`docs/generator-options.md` §3 gives the rule.

Scenario ids, titles and the directory a repository is generated into do
describe the scenario, and a fix necessarily names what it repairs. The full
policy, including what is deliberately not hidden and how predictions may name a
commit (`evaluate --reference-format`), is in
[docs/decisions/oracle-leakage.md](docs/decisions/oracle-leakage.md); it is
checked by `validate --lint` and by `tests/test_no_oracle_leakage.py`.

## Directory structure

The tracked top-level files and directories are as follows, with every module of `src/szzbench/`.

```text
SZZBench/
├── pyproject.toml
├── README.md
├── LICENSES.md
├── LICENSE-MIT
├── LICENSE-CC-BY-4.0
├── .gitignore
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── src/
│   └── szzbench/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── scenario.py
│       ├── validator.py
│       ├── operations.py
│       ├── generator.py
│       ├── verifier.py
│       ├── scenario_builder.py
│       │
│       ├── graph_scenario.py
│       ├── graph_validator.py
│       ├── graph_simulator.py
│       ├── graph_operations.py
│       ├── graph_generator.py
│       ├── graph_verifier.py
│       ├── graph_scenario_builder.py
│       │
│       ├── bulk_generator.py
│       ├── manifest.py
│       ├── cleaner.py
│       ├── index_splice.py
│       ├── retired_ids.py
│       ├── readme.py
│       │
│       ├── evaluator.py
│       ├── policies.py
│       ├── baselines.py
│       ├── coverage.py
│       │
│       ├── findings.py
│       ├── gitutils.py
│       └── paths.py
│
├── scenarios/
│   ├── index.yml
│   ├── SZZ-0006/
│   │   ├── scenario.yml
│   │   └── README.md
│   └── ...
│
├── advanced-scenarios/
│   ├── index.yml
│   ├── SZZG-0001/
│   │   ├── scenario.graph.yml
│   │   └── README.md
│   └── ...
│
├── docs/
│   ├── validation.md
│   ├── generator-options.md
│   ├── evaluation-policies.md
│   ├── baselines.md
│   ├── scenario-readme.md
│   ├── retired-ids.md
│   └── decisions/
│
├── examples/
│   ├── pydriller-run/
│   ├── pyszz-run/
│   ├── szz-unleashed-run/
│   └── token-bszz-run/
│
├── tools/
│   ├── adapters/
│   ├── scenario-editor/
│   └── generated-repo-viewer/
│
└── tests/
    ├── README.md
    ├── conftest.py
    ├── support.py
    └── test_*.py
```

The main roles are as follows.

| Path | Role |
|---|---|
| `src/szzbench/` | Main Python implementation. Contains the CLI; the validator, generator, verifier and skeleton builder of each scenario type; the modules that generate the whole suite, check the indexes and render the scenario README headers; the evaluator, baselines and coverage; and the shared helpers. |
| `scenarios/` | Location for normal `SZZ-XXXX` scenarios. |
| `advanced-scenarios/` | Location for Graph `SZZG-XXXX` scenarios. |
| `docs/` | Reference documentation: the validation codes, the generator options, the evaluation policies, the baselines, the scenario README header and the retired scenario ids. `docs/decisions/` records the design decisions behind them. |
| `examples/` | Recorded runs of third-party SZZ implementations over the shipped suite, each with its predictions and evaluation report. |
| `generated-input-repos/` | Output location for Git repositories generated by the generator. This is not tracked by Git. |
| `tools/adapters/` | Example adapters that convert SZZ tool-specific outputs into SZZBench predictions. |
| `tools/scenario-editor/` | Local Web application for creating normal scenarios. |
| `tools/generated-repo-viewer/` | Local Web application for inspecting generated Git repositories. |
| `tests/` | Test code. `tests/README.md` says what the suite needs. |
| `.github/workflows/` | CI. |
| `LICENSES.md` | Which licence covers which files: the MIT License (`LICENSE-MIT`) for the software, CC BY 4.0 (`LICENSE-CC-BY-4.0`) for the scenarios and the documentation. |

## Installation

Python 3.10 or later is required.

Git 2.29 or later is required as well. SZZBench runs Git isolated from your own Git configuration, so signing, hooks and global ignore or attributes files do not affect what it generates (`docs/generator-options.md` §5). A JDK (`javac` and `java`) is needed only by the tests that compile or run scenario code, which are skipped without one, and Node.js only by the tools under `tools/`.

The test suite runs in CI on Linux twice (`.github/workflows/tests.yml`): with Python 3.14 and the current Git of GitHub's `ubuntu-latest` runner, and with Python 3.10 and Debian 12's Git 2.39. SZZBench is developed on macOS. Windows is not tested; the PowerShell commands below are given for convenience ([#109](https://github.com/higolab/SZZBench/issues/109)).

Create and activate a virtual environment in the SZZBench root directory.

On macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Then install SZZBench.

```bash
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev]"
```

`-e` means editable install. It directly references the source code under development, so changes under `src/szzbench/` are usually reflected without reinstalling.

If you do not need development dependencies, install without the `dev` extra.

```bash
python -m pip install -e .
```

After installation, the `szzbench` command becomes available.

```bash
szzbench --help
```

When returning to this project later, activate the virtual environment again before running `szzbench`, `pytest`, or other project commands.

On macOS / Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Using normal scenarios

### validate

Validate the structure and references in `scenario.yml`.

```bash
szzbench validate scenarios/SZZ-0006/scenario.yml
```

Use `--simulate` to validate operations by simulating them in memory.

```bash
szzbench validate --simulate scenarios/SZZ-0006/scenario.yml
```

Use `--strict` to treat warnings as failures.

```bash
szzbench validate --simulate --strict scenarios/SZZ-0006/scenario.yml
```

Use `--json` to output the result as JSON.

```bash
szzbench validate --simulate --json scenarios/SZZ-0006/scenario.yml
```

Use `--lint` to run the opt-in lints as well. They check what a good scenario looks like, such as neutral commit messages, the controlled vocabularies and the generated README header (`docs/validation.md`). `--lint` implies `--simulate`.

```bash
szzbench validate --lint --strict scenarios/SZZ-0006/scenario.yml
```

### generate

Generate an actual Git repository from `scenario.yml`.

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force
```

Add `--no-verify` to skip verification after generation.

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force   --no-verify
```

When verification finds an error, `generate` prints the findings after `[ERROR] GENERATION_FAILED: Generated repository failed verification.` and exits 1. The output keeps `metadata/verify-result.json`, `generation.log` and `generation-error.json`, but has no `manifest.json`, so `generate-all-repos` generates it again.

A verification warning (such as `W703`, basic blame does not reach the expected BIC) is printed and leaves the exit code 0. Add `--strict` to exit with 1 on a warning, as `verify --strict` does; the output is complete and kept either way. `--strict` cannot be combined with `--no-verify`. Add `--json` to print one JSON document on stdout and nothing else: `kind`, `scenario`, `output_dir`, `status` (`generated` or `failed`), `commit_count`, `error`, and `verification`, which is what `verify --json` prints (the counts and the findings), or `null` with `--no-verify`. A failed generation prints the document too, and exits 1.

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force   --strict   --json
```

`--force` replaces an existing `--out` only when it is a previous generated output, or a directory that holds nothing but `repo/` and `metadata/`. It refuses, and deletes nothing, when `--out` is a file, holds anything else, contains the scenario file, or is the current directory or one of its parents. The same rule applies to `generate-graph` and to `generate-all-repos`.

The generated directory has the following structure.

```text
generated-input-repos/SZZ-0006/default/
├── repo/
│   ├── .git/
│   └── ...
└── metadata/
    ├── scenario.yml
    ├── commit-map.json
    ├── validation-result.json
    ├── verify-result.json
    └── generation.log
```

### verify

Verify that a generated repository corresponds to `scenario.yml` and is still as the generator left it: every commit of `commit-map.json` reachable from a ref, with the author and dates the map records, the default branch at the last commit and checked out, and a clean index and working tree (E600–E609 in [docs/validation.md](docs/validation.md)). A repository an SZZ tool has checked out or committed in fails `verify`, but `evaluate` still scores it as long as every commit is reachable.

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml
```

You can also explicitly specify `commit-map.json` if necessary.

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml   --commit-map generated-input-repos/SZZ-0006/default/metadata/commit-map.json
```

Use `--strict` to exit with 1 on a warning as well as on an error (such as `W703`, basic blame does not reach the expected BIC), and `--json` to output the result as JSON.

### new-scenario

Create a skeleton for a new normal scenario.

```bash
szzbench new-scenario   --title "Formatting after bug introduction"   --category "Intermediate noise and history noise"   --tier control   --factor formatting-noise   --factor intermediate-history
```

By default, a directory like the following is created, and `scenarios/index.yml` is also updated.

```text
scenarios/SZZ-XXXX/
├── scenario.yml
└── README.md
```

The new entry goes at the end of the index's `scenarios:` list, in the format of the shipped entries, and no other line of the index changes. If the edited index would not load, the command writes nothing and exits with status 1.

The skeleton is the smallest history a scenario can have: `c0` writes a `Range` class, `c1` narrows its range check and `c2` restores it, with `c1` as the expected BIC and `c2` as the BFC. `szzbench validate --simulate --strict --lint` accepts it as it is, so the lints check the factors and the commit messages from the first run; at most it reports the information item `I413`, when the author the generator gives `c1` wrote nothing else. Replace the history, the bug and the checks with the scenario's own.

`--category` names a category of [docs/decisions/vocabulary.md](docs/decisions/vocabulary.md), section 3, by its code (`S3`) or its name (`Intermediate noise and history noise`); both go into `meta` and the index entry, and any other value is refused. `--tier` is required and has no default: it declares what the scenario is for, `control` or `discriminating` (section 7), and a `discriminating` skeleton also lists every family under `meta.defeats`, as the tier requires. At least one `--factor` is required. The factor vocabulary is open, but a factor that `--lint` rejects, a schema key or operation name (`E400`) or a mix of hyphens and underscores (`E402`), is refused, and so is a factor that contains whitespace. A refused option writes nothing, and the command exits with status 1 (status 2 for an option argparse refuses).

`--difficulty` takes `easy`, `medium` or `hard` (default `medium`); `szzbench coverage` checks it against the measured floor once the repository is generated. The slug, which goes into `meta.slug`, the index entry and the repository name, is made from the title unless `--slug` gives it. `--status` sets `meta.status` to `draft` (default) or `active`; `retired` belongs to a scenario that has been removed ([docs/retired-ids.md](docs/retired-ids.md)). `--root` creates the scenario under another suite root than `scenarios/` and updates that root's `index.yml`.

## Using Graph scenarios

### validate-graph

Validate the structure and references in `scenario.graph.yml`.

```bash
szzbench validate-graph advanced-scenarios/SZZG-0001/scenario.graph.yml
```

Use `--simulate` to simulate Graph operations. They are replayed in memory, except in a scenario with commits that Git computes during generation (merges, real cherry-picks and reverts, patch operations, conflict resolutions): such a scenario is generated with Git in a temporary directory instead (`docs/validation.md`).

```bash
szzbench validate-graph   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

Use `--strict-paths` for stricter checks of path / entity shapes.

```bash
szzbench validate-graph   --strict-paths   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

`--strict`, `--lint` and `--json` work as they do for `validate`. The Graph lints are static, so `--lint` does not imply `--simulate` here, and they run only when no error was found.

### generate-graph

Generate an actual Git repository from `scenario.graph.yml`.

```bash
szzbench generate-graph   advanced-scenarios/SZZG-0001/scenario.graph.yml   --out generated-input-repos/SZZG-0001/default   --force
```

The generated directory has the following structure.

```text
generated-input-repos/SZZG-0001/default/
├── repo/
│   ├── .git/
│   └── ...
└── metadata/
    ├── scenario.graph.yml
    ├── commit-map.json
    ├── graph-map.json
    ├── validation-result.json
    ├── verify-result.json
    └── generation.log
```

`commit-map.json` records the mapping between logical commit IDs and actual Git hashes.

`graph-map.json` records additional information for Graph scenarios. It includes information such as branches, parents, and roles. A commit's `parents` and `parent_hashes` are its declared parents. For a commit that owns `commit_generator` operations, Git's first parent is its last generated commit, listed in `generated_commits` (`docs/generator-options.md` §2). `head` records where generation left HEAD: `branch`, the branch it is on (null when HEAD is detached), and `hash`, the commit. HEAD stays on the branch of the scenario's last commit, which need not be the default branch (see "What the generated repositories do not reveal" and `docs/generator-options.md` §3).

When verification finds an error, `generate-graph` prints the findings and records the failure as `generate` does. `--no-verify`, `--strict` and `--json` work as they do for `generate`; `kind` is `graph`.

### verify-graph

Verify that a generated repository corresponds to `scenario.graph.yml`. Besides the commits and the bug locations, it checks that the repository is still as generation left it: the branches and tags that `graph-map.json` records, HEAD, and a clean index and working tree. A repository in which an SZZ tool has checked out, committed or branched therefore fails verification, although the staleness check of `generate-all-repos` and `evaluate` accepts it (`docs/generator-options.md` §6).

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml
```

You can also explicitly specify `commit-map.json` and `graph-map.json` if necessary.

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml   --commit-map generated-input-repos/SZZG-0001/default/metadata/commit-map.json   --graph-map generated-input-repos/SZZG-0001/default/metadata/graph-map.json
```

`--strict` and `--json` work as they do for `verify`.

### new-graph-scenario

Create a skeleton for a new Graph scenario.

```bash
szzbench new-graph-scenario   --title "BIC on feature branch and BFC on main"   --category G4   --tier control   --factor branch-merge
```

`--difficulty` takes `easy`, `medium` or `hard` (default `medium`; `advanced` is retired) and, like the classic suite's, is checked against the measured floor by `szzbench coverage` once the repository is generated (see [docs/decisions/vocabulary.md](docs/decisions/vocabulary.md), section 4).

By default, a directory like the following is created, and `advanced-scenarios/index.yml` is also updated.

```text
advanced-scenarios/SZZG-XXXX/
├── scenario.graph.yml
└── README.md
```

As with `new-scenario`, the entry goes at the end of the `scenarios:` list, in the shape both indexes share (issue #200), and nothing is written if the edited index would not load.

`--category`, `--tier`, `--factor`, `--slug`, `--status` and `--root` work as they do for `new-scenario`, with `advanced-scenarios/` as the default root; a refused factor is named with its graph code (`GE400`, `GE402`). The Graph index entry has the keys of a classic one, `slug` and `readme` included. The skeleton has the same three commits, on `main`, and its README's `## Expected history` block is rendered from them, so `szzbench validate-graph --simulate --strict --strict-paths --lint` accepts it as it is, with at most `GI413`.

## validate-index

Check `scenarios/index.yml` and `advanced-scenarios/index.yml` against the scenario directories: every scenario directory has an entry and every entry a scenario file and a README, no entry uses a retired id, and the fields an entry copies from its scenario's `meta`, such as the title, the status and the factors, are all there and still agree with it. Both indexes have one shape: `scenarios:` and nothing else at the top, and the same ten keys in every entry (issue #200). The index repeats those fields, which is how it drifted before (issue #19).

```bash
szzbench validate-index
szzbench validate-index --json
```

The command exits with 1 on any error; the codes, IE001–IE047, are listed in [docs/validation.md](docs/validation.md). `--scenarios-root` and `--advanced-scenarios-root` check the indexes of other suite roots than `scenarios/` and `advanced-scenarios/`, and `--json` outputs the result as JSON. `new-scenario`, `new-graph-scenario` and the Scenario editor add their entries themselves, so the command is mainly a check on hand edits.

## evaluate

Evaluate SZZ tool predictions against SZZBench commit-level oracles.

```bash
szzbench evaluate \
  --predictions predictions.jsonl \
  --generated-root generated-input-repos \
  --include-generated \
  --evaluation-variant origin-aware \
  --out generated-szz-results/my-tool
```

`--predictions` accepts JSON or JSONL. The common prediction format can be one record per scenario, including scenarios with no predictions:

```jsonl
{"scenario_id":"SZZ-0047","predictions":[]}
{"scenario_id":"SZZ-0006","predictions":[{"fix_commit":"<actual hash>","inducing_commit":"<actual hash>"}]}
```

It can also be one record per predicted BIC:

```jsonl
{"scenario_id":"SZZ-0006","fix_commit":"<actual hash>","inducing_commit":"<actual hash>"}
```

`scenario_id` and `inducing_commit` are required for evaluation; `fix_commit` is optional, but a scenario with several bug-fixing commits is also scored per fix: a prediction counts for the fix its `fix_commit` names, and one without `fix_commit` for every fix (`docs/evaluation-policies.md` §1.7). `inducing_commit` may be an actual Git hash, a unique hash prefix, or a logical commit id from `commit-map.json`. A hash or a prefix may be in either letter case, and whitespace around a reference, such as a trailing newline, is ignored; a logical id is written as `commit-map.json` writes it. A reference that resolves to no commit fails the scenario, is listed in `unknown_predictions`, and counts as a false positive in precision.

A record can also say that the tool failed on the scenario; the scenario then fails whatever the record predicts (`docs/evaluation-policies.md` §1.6):

```jsonl
{"scenario_id":"SZZ-0006","status":"error","errors":["<what went wrong>"],"predictions":[]}
```

The adapters also write `repository_id`, the id of the generated repository the tool ran on; a record made on another generation of the scenario fails as stale.

A record that cannot be read is a loading error: `predictions` that is not a list (`null` included), a prediction without an `inducing_commit` or with one that is not a non-empty string, a `rank`, `fix_commit`, `status` or `repository_id` of the wrong kind, or both a `predictions` list and a top-level `inducing_commit`. `evaluate` then exits 1, and the scenario the record names fails as `run_status: invalid`, whatever its other records predict (`docs/evaluation-policies.md` §1.6). Until issue #138 a record whose predictions could not be read was scored as an empty answer, which passes an `expect_no_bic` scenario.

Use `--include-generated` to evaluate every generated repository under `--generated-root`. A scenario that no record names then fails as a missing record (`run_status: missing`) rather than being read as an abstention, so write an empty record, like `SZZ-0047` above, for a scenario on which the tool ran and found nothing. The adapters under `tools/adapters/` write such records.

`evaluate` exits with 1 when the report has an error, such as a loading error or a stale generated output, and otherwise with 0, however many scenarios fail. Add `--fail-on-non-pass` to exit with 1 also when any scenario is not PASS (`docs/evaluation-policies.md` §1.6).

A run that scores no scenario at all, such as one over an empty predictions file or over a `--generated-root` without outputs, is an error (`EVALUATE_FAILED`, exit 1), with or without `--fail-on-non-pass`; `--include-generated` refuses a `--generated-root` that does not exist (issue #141).

For Graph scenarios, `--evaluation-variant` selects a named `expected_szz.evaluation_variants` entry such as `direct-only`, `origin-aware`, or `relaxed-with-credit`. If it is omitted, SZZBench uses the scenario's `default_variant` when one is defined, otherwise it uses `expected_szz.commit_level`. A scenario that does not define the requested name is scored as if the option were omitted, with a note naming the oracle used, and the run reports those scenarios in one warning; an empty name is the same as omitting the option. Classic scenarios have no variants, and the run says so once (`docs/evaluation-policies.md` §1.3). Hyphen and underscore differences are normalized for matching. This option is independent of `--variant`, which selects the generated repository directory under each scenario.

The JSON report keeps the strict fields (`true_positives`, `false_positives`, `false_negatives`), reports `unknown_predictions`, `run_status` and `run_errors` per scenario, and also includes Graph-specific details when available: `evaluation_policy`, `evaluation_variant`, `hard_false_positives`, `related_origin_hits`, `related_but_not_correct_hits`, `acceptable_related_hits`, `weighted_credit`, `minimum_required_met`, and `top_k`.

`--json` prints that report on stdout instead of the summary, and `--out` writes it to `evaluation-results.json`, with `evaluation-results.md` beside it. `--scenarios-root` and `--advanced-scenarios-root` say where the scenario files are when they are not under `scenarios/` and `advanced-scenarios/`. `--reference-format` restricts how a prediction may name a commit: `hash` accepts only hashes and hash prefixes, which is all a tool that reads the repository can produce; `logical` only logical ids such as `c1`, for adapters and test fixtures; and `auto`, the default, both. A rejected reference is an unknown prediction (`docs/decisions/oracle-leakage.md`).

A tool is run on a generated repository from the bug-fixing commit: the adapters under `tools/adapters/` take it from the scenario and `metadata/commit-map.json` and hand its hash to the tool. A tool that walks history from HEAD instead, such as one that runs `git log` without `--all`, may miss the bug-fixing commit of a Graph scenario, because `generate-graph` leaves HEAD on the branch of the scenario's last commit, which need not contain it (see "What the generated repositories do not reveal"; `metadata/graph-map.json` records HEAD as `head`).

For SZZ Unleashed, the adapter runs the tool too: build its jar ([examples/szz-unleashed-run/README.md](examples/szz-unleashed-run/README.md)) and pass it with `--jar`. `--depth` is SZZ Unleashed's `-d`, the depth of its line mapping graph (default 3, its own), and changes the results a great deal; that README records a run at depth 3 and at depth 1. Without `--jar`, the adapter only converts the `fix_and_introducers_pairs.json` files an earlier run left under `generated-input-repos/<SCENARIO_ID>/default/szz-unleashed/run-depth<depth>/`.

```bash
tools/adapters/szz_unleashed_to_predictions.py \
  --jar /path/to/szz_find_bug_introducers-0.1.jar \
  --generated-root generated-input-repos \
  --out generated-szz-results/szz-unleashed/predictions.jsonl
```

For PyDriller, run the adapter against the generated repositories:

```bash
tools/adapters/pydriller_to_predictions.py \
  --pydriller-path /path/to/pydriller \
  --generated-root generated-input-repos \
  --out generated-szz-results/pydriller/pydriller-predictions.jsonl

szzbench evaluate \
  --predictions generated-szz-results/pydriller/pydriller-predictions.jsonl \
  --generated-root generated-input-repos \
  --include-generated \
  --out generated-szz-results/pydriller
```

For PySZZ's B-, AG-, MA-, L- and R-SZZ, `tools/adapters/pyszz_variants_to_predictions.py` runs PySZZ itself and writes one predictions file per variant. [examples/pyszz-run/README.md](examples/pyszz-run/README.md) says what to install, including the library versions and srcML that PySZZ's results depend on, and records a run of all five over the shipped suite.

For B-SZZ on token-level histories, `tools/adapters/token_bszz_to_predictions.py` rewrites each generated repository to one token per line with cregit, in a Docker image built from `tools/adapters/token-bszz/`, runs PySZZ's B-SZZ on the rewritten copies, and names each answer by the original repository's commit. [examples/token-bszz-run/README.md](examples/token-bszz-run/README.md) says what to install and records a run over the shipped suite.

## baselines

Score the declared families of naive predictors over the generated repositories with the ordinary evaluator: the floor described under "What the benchmark does not test" above. [docs/baselines.md](docs/baselines.md) describes the families and what they measure on the shipped suite.

```bash
szzbench baselines --out results/floor
szzbench baselines --family position --family blame
```

`--family` runs only the named families, `metadata`, `position`, `shape` or `blame`, and can be repeated; the default is all four. A run limited this way does not say which `control` scenarios no naive rule solves. `--out` writes `baselines.json` and `baselines.md` to a directory, and `--json` prints the report as JSON. `--generated-root` and `--variant` select the generated repositories, and `--scenarios-root` and `--advanced-scenarios-root` the scenario files, as for `evaluate`. A stale output is not scored but reported as an error, and any error exits with 1.

## coverage

Measure what each scenario contributes, as described under "What the benchmark does not test" above: the size of its oracle, the depth of its bug-introducing commit, its distractors, the size and branchiness of its history and `blame_class`, with the scenarios grouped by the shape they share ([docs/baselines.md](docs/baselines.md)).

```bash
szzbench coverage --out results/coverage
```

`--out` writes `coverage.json` and `coverage.md` to a directory. `--json`, `--generated-root`, `--variant`, `--scenarios-root` and `--advanced-scenarios-root` work as they do for `baselines`, and so does the exit code.

## generate-all-repos

Generate repositories for all normal scenarios under `scenarios/` and all Graph scenarios under `advanced-scenarios/` with one command.

```bash
szzbench generate-all-repos
```

The command scans the following files.

- `scenarios/*/scenario.yml`
- `advanced-scenarios/*/scenario.graph.yml`

Each generated repository is written under `generated-input-repos/<SCENARIO_ID>/default/`. `--scenarios-root` and `--advanced-scenarios-root` scan other suite roots, and `--out-root` writes under another root than `generated-input-repos/`; like the defaults, they are relative to the current directory. Only the scenario directories directly under each root are read. The command stops before it writes anything when the two roots hold the same id (letter case aside, since a case-insensitive file system would give both one output) or when `--out-root` is a scenario root or lies inside one (issue #168).

Every generation writes `metadata/manifest.json` last. It records the scenario file's hash, a fingerprint of the generator's code, and the repository id that prediction records carry. An existing output is skipped only when that manifest still matches and the output still has everything it describes. An output without one (an interrupted generation, or one made before 2026-09-29), with one that cannot be read or parsed (the reason says why), whose scenario file or generator code has changed since, or that has lost part of what the manifest describes (such as its repository, one of its commits, its commit map or its copy of the scenario) is stale and is regenerated, with the reason printed (`docs/generator-options.md` §6). The command is therefore safe to run repeatedly: it brings every output up to date and leaves current ones alone. `evaluate`, `baselines` and `coverage` refuse to score a stale output.

To remove existing generated repositories and create them again, use `--overwrite`.

```bash
szzbench generate-all-repos --overwrite
```

`--overwrite` generates each scenario again even when its output is current. Every generation, of a stale output too, writes into `generated-input-repos/<SCENARIO_ID>/default.tmp/`, and the new output replaces `default/` only once it has been generated and verified: the previous output is moved aside to `default.old/` and removed after the new one is in place (issue #168).

A scenario that fails does not stop the run: it is listed as `Failed`, with the error, and the command goes on with the next scenario, prints its summary and exits 1. An error that is not a generation error (a crash in SZZBench) is listed with its traceback, and a generation that fails verification with the verification errors. The previous output, if there is one, is left in place, and the files of the failed attempt (`generation.log`, `generation-error.json` and, after a failed verification, `metadata/verify-result.json`) stay in `<SCENARIO_ID>/default.tmp/`; the `Failed` line says where. A `default.old/` that could not be removed after a replacement is printed as a warning (`SZZ-0005: [WARNING] the previous output, moved aside to …`), and the next run removes it.

Add `--no-verify` to skip post-generation verification for all generated repositories.

```bash
szzbench generate-all-repos --no-verify
```

The verification warnings of every output are printed to stderr, one line each, after the scenario id (`SZZ-0078: [WARNING] W703: ...`), and the summary counts the outputs with a warning as `Warned`. An output skipped as up to date reports the verification its generation recorded in `metadata/verify-result.json`; one without a readable `verify-result.json` is generated again. Add `--strict` to exit with 1 when the verification of any output warns (it cannot be combined with `--no-verify`), and `--json` to print one JSON document on stdout and nothing else: `items` (one per scenario, with the keys of `generate --json` and `scenario_id`, `overwritten`, `stale_reason`, `traceback` and `leftover`, the warning about a `default.old/` left behind or `null`), `orphans`, and `summary` with the counts of the text summary.

```bash
szzbench generate-all-repos --strict
szzbench generate-all-repos --json
```

## readme

Check that every scenario README opens with the header generated from its scenario file, or regenerate the headers.

```bash
szzbench readme
szzbench readme scenarios
```

The header — title, category, tier, status, difficulty, language, factors, the oracle as the evaluator resolves it and, for Graph scenarios, the graph-only features the scenario uses — is the only part of a README a tool writes; the prose after it belongs to the author and is never touched. `szzbench readme` exits with 1 when a header is missing or no longer matches the scenario, and `validate --lint` / `validate-graph --lint` report the same disagreement as `W455` / `GW455`. A suite root (`scenarios`, `advanced-scenarios`), a scenario directory or a scenario file limits the check to those scenarios, and a target that resolves to no scenario file is an error (exit 1) (issue #188). Without a target, the command checks the scenarios under `--scenarios-root` and `--advanced-scenarios-root` (default `scenarios` and `advanced-scenarios`). `--json` prints the report as JSON.

```bash
szzbench readme --write
szzbench readme --write advanced-scenarios/SZZG-0022
```

`--write` regenerates the stale, malformed or missing headers, for both suites or for the scenarios named on the command line. A header edited out of its generated shape is replaced whole, so one header remains, and a README's BOM and CRLF line endings are kept. `--write` checks what it wrote and exits with 1 when a README is still stale. See [docs/scenario-readme.md](docs/scenario-readme.md).

## clean

Delete generated repositories under `generated-input-repos/`.

```bash
szzbench clean
```

Use `--dry-run` to only check what would be deleted.

```bash
szzbench clean --dry-run
```

You can also explicitly specify the target root.

```bash
szzbench clean --root generated-input-repos
```

`clean` can be used for generated outputs from both normal scenarios and Graph scenarios.

`clean` removes every generated output below its root, at any depth. It therefore refuses a root that is the file-system root, the home directory, or the current directory or one of its parents, and scans nothing. Under any root other than `generated-input-repos` of the current directory, it lists the outputs it found on stderr and asks before removing them; `--yes` removes them without asking. Where stdin is not a terminal, such as in a script, it refuses without `--yes` and removes nothing. `--dry-run` never asks. `--json` prints one JSON document on stdout: `root`, `dry_run`, `outputs` and `summary` (`found` and `removed`).

```bash
szzbench clean --root /tmp/szzbench-repos --dry-run
szzbench clean --root /tmp/szzbench-repos --yes --json
```

## Auxiliary tools

### Scenario editor

`tools/scenario-editor/` is a local Web application for creating normal `scenario.yml` scenarios.

```bash
cd tools/scenario-editor
npm ci
npm run dev
```

Open the following URL in a browser.

```text
http://127.0.0.1:5173
```

This editor can create `scenario.yml` and `README.md` by entering metadata, source-code versions, and BIC / BFC information. Through a local Node.js API, it can also save files directly under `scenarios/SZZ-XXXX/`. Saving requires a `meta.tier`, runs `szzbench validate --lint` on the files first (an error rejects the save), and inserts the generated README header; the backend needs a Python with SZZBench's dependencies (`tools/scenario-editor/README.md`).

At present, it is mainly intended for normal scenarios. It does not support editing Graph scenarios.

### Generated repository viewer

`tools/generated-repo-viewer/` is a local Web application for inspecting generated Git repositories.

```bash
cd tools/generated-repo-viewer
npm ci
npm run dev
```

Open the following URL in a browser.

```text
http://127.0.0.1:5174
```

This viewer reads actual Git repositories under `generated-input-repos/` and displays information by running commands such as `git log`, `git show`, `git diff`, and `git blame` through a Node.js backend.

It mainly allows you to check the following:

- generated repository list
- scenario metadata
- mapping between logical commit IDs and Git hashes
- commit timeline
- file list at each commit
- file content
- diff
- blame
- bug oracle
- `verify-result.json`
- `validation-result.json`
- `generation.log`

## Tests

If development dependencies are installed, run tests with the following command.

```bash
pytest
```

To run a specific test, for example:

```bash
pytest tests/test_generator_smoke.py
```

[tests/README.md](tests/README.md) says what the suite needs (a JDK, Node.js for the Scenario Editor's tests) and where its shared helpers are. The same suite runs in CI on every push to `main`, and CI also builds the two web tools under `tools/`. Pull request CI is temporarily paused; [tests/README.md](tests/README.md) explains how to resume it.

## Files that should not be tracked by Git

The following files and directories should not be tracked by Git.

```text
generated-input-repos/
generated-szz-results/
generated-metadata/
results/
outputs/
tmp/
temp/
node_modules/
.venv/
venv/
__pycache__/
.pytest_cache/
dist/
build/
```

Dependencies for JavaScript/TypeScript tools are installed under `node_modules/`, but this directory should not be tracked by Git. If needed, recreate it by running `npm ci` in each tool directory, which installs the versions recorded in its `package-lock.json` and leaves that file as it is.

Python virtual environments such as `.venv/` should also not be tracked by Git. Recreate them in each local environment when needed.

## Creating a distribution ZIP

To create a ZIP file that contains only files tracked by Git, use the following command.

```bash
git archive --format=zip --prefix=SZZBench/ --output=SZZBench_source.zip HEAD
```

This creates a ZIP file that excludes files not tracked by Git, such as `node_modules/`, `.venv/`, and `generated-input-repos/`.

## Current notes

- `scenario.graph.yml` is more expressive than the normal `scenario.yml`; its schema is versioned `graph-1.0` and is no longer a draft (`docs/decisions/vocabulary.md` §4).
- For Graph scenarios, both `validate-graph --simulate` and `verify-graph` are recommended because the history structures and oracles are complex.
- Generated repositories are derived artifacts, so they should generally not be tracked by Git.
- SZZBench is not intended to replace large real-project-based oracles. It is a complementary benchmark for checking SZZ failure modes with small, controlled histories.

## Authors and license

SZZBench is developed by Yoshiki Higo and Inase Kondo (The University of Osaka) and Masanari Kondo and Yasutaka Kamei (Kyushu University).

The software (`src/`, `tests/` and the code under `tools/`) is licensed under the MIT License ([`LICENSE-MIT`](LICENSE-MIT)), and the scenarios, the examples and the documentation under CC BY 4.0 ([`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)). [`LICENSES.md`](LICENSES.md) lists which files each licence covers and gives the attribution for the CC BY 4.0 materials: "The SZZBench authors, *SZZBench*, https://github.com/higolab/SZZBench".
