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

`szzbench baselines` scores a declared family of cheap predictors — metadata
only, history position only, file-touch shape, and the classic blame baseline —
with the ordinary evaluator, so every result on SZZBench can be read against a
floor. Measured on the shipped suite of 279 scenarios: **"report the second
commit of the history", which opens no file at all, solves 160/279 — four more
than the classic `blame-deleted-lines` baseline at 156/279**, and the lead has
changed hands with every batch of new scenarios. Some cheap rule solves 233 of
the 279 scenarios, an oracle-aware upper bound rather than an attacker's score;
the forty-six it does not reach all have a multi-commit oracle, which is
forced rather than chosen: a one-commit answer is always named by one of the
positional rules, and an empty one by `abstain`. The metadata
family is at chance, which is the leakage guarantee below holding.

Every scenario declares `meta.tier`: **233 are `control`** — they check that a
method handles a specific input condition, and a cheap rule may well solve them
— and **46 are `discriminating`**, which no declared cheap baseline solves.
Thirty-four of those were designed against one axis: the answer is two commits,
and the fix's deleted lines do not blame to one of them. Five more fail the cheap
rules differently — SZZ-0218's and SZZ-0220's answers are entirely reachable by
blame, which also hands over commits that are not answers; SZZ-0222's blame
answer contains no required commit at all; and SZZG-0148 and SZZG-0149 name
three commits under a credit threshold of two. The remaining seven were not
designed for the tier: they are older scenarios that turned out to resist every
cheap rule. Every one of the seventeen categories has at least two, so a method
cannot pass a category by overfitting to a single history. A control being
cheaply solvable is not a defect; what the tier prevents is reading a
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

Score the declared families of cheap predictors over the generated repositories with the ordinary evaluator: the floor described under "What the benchmark does not test" above. [docs/baselines.md](docs/baselines.md) describes the families and what they measure on the shipped suite.

```bash
szzbench baselines --out results/floor
szzbench baselines --family position --family blame
```

`--family` runs only the named families, `metadata`, `position`, `shape` or `blame`, and can be repeated; the default is all four. A run limited this way does not say which `control` scenarios no cheap rule solves. `--out` writes `baselines.json` and `baselines.md` to a directory, and `--json` prints the report as JSON. `--generated-root` and `--variant` select the generated repositories, and `--scenarios-root` and `--advanced-scenarios-root` the scenario files, as for `evaluate`. A stale output is not scored but reported as an error, and any error exits with 1.

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

---

# 日本語版

# SZZBench

SZZBench は、SZZ 手法を評価するための人工 Git リポジトリ生成・検証ツールです。

SZZ では、バグを修正したコミットから過去の履歴をたどり、そのバグを混入した可能性が高いコミットを推定します。SZZBench は、この推定がどのような履歴ではうまく動き、どのような履歴では失敗しやすいのかを、制御された小さな Git リポジトリで確認するための基盤です。

## クイックスタート

クローン直後から評価レポートまでの最短経路です。最後のコマンドは、第三者の SZZ 実装を実際に走らせた
結果を再採点するので、この環境が元の環境と一致しているかの確認にもなります。仮想環境を有効化する行は
macOS / Linux 向けです。Windows については [インストール](#インストール) を参照してください。

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

`generate-all-repos` は `generated-input-repos/` に 279 個のリポジトリを生成し、3 分ほどかかります。
それ以降は数秒です。評価は `PASS: 161`、`FAIL: 118`、precision 0.781、recall 0.689 を出力します。
その実行が何であったか、どう作られたか、数値が何を意味するかは
[examples/pydriller-run/README.md](examples/pydriller-run/README.md) にあります。`control` の 68.7 %、
`discriminating` の 2.2 % に成功する理由もそこで説明しています。

この先を読む前に、もう 2 つ知っておくとよいコマンドがあります。

```bash
szzbench baselines --out results/floor
szzbench coverage --out results/coverage
```

前者は解析を一切行わない規則の得点、すなわち SZZBench 上のあらゆる結果を読む際の床を出します。後者は
各シナリオが何に寄与しているかを報告します。自分のツールを評価するには、同じ形式の JSONL を作って
`szzbench evaluate` に渡してください。形式は [evaluate](#evaluate-1) にあります。

## 用語

| 用語 | 意味 |
|---|---|
| SZZ | バグ修正コミットから、バグ混入コミットを推定する手法群。名前は Śliwerski, Zimmermann, Zeller に由来します。 |
| BFC | Bug-Fixing Commit。バグを修正したコミット。 |
| BIC | Bug-Inducing Commit。バグを混入したコミット。 |
| oracle | 正解情報。どのコミットが BIC / BFC か、どの行や要素が fault / fix かを記述します。 |
| scenario | 人工履歴を記述したファイル。通常シナリオでは `scenario.yml`、複雑シナリオでは `scenario.graph.yml` を使います。 |

## SZZBench の2種類のシナリオ

SZZBench には、大きく分けて2種類のシナリオがあります。

### 1. 通常シナリオ: `SZZ-XXXX`

通常シナリオは、比較的シンプルな履歴を扱います。

```text
scenarios/
└── SZZ-0006/
    ├── scenario.yml
    └── README.md
```

主な想定は以下です。

- 直線履歴
- 単一 branch
- `write_file` / `replace` を中心とした操作
- 1つ、または少数の BIC / BFC
- 小さく読みやすい人工履歴

通常シナリオでは、次のコマンドを使います。

```bash
szzbench validate
szzbench generate
szzbench verify
szzbench new-scenario
```

### 2. Graph シナリオ: `SZZG-XXXX`

Graph シナリオは、通常の `scenario.yml` では表現しにくい複雑な履歴を扱います。

```text
advanced-scenarios/
└── SZZG-0001/
    ├── scenario.graph.yml
    └── README.md
```

主な想定は以下です。

- branch / merge
- cherry-pick / backport
- rename / move / copy / delete
- 複数 BIC / 複数 BFC
- direct BIC / origin BIC / contributing BIC
- work item / issue / developer hint
- top-k や relaxed evaluation などの評価ポリシー

`scenario.graph.yml` が持てるキーは [docs/graph-schema.md](docs/graph-schema.md) に一覧があります。それ以外のキーには `validate-graph` が警告を出します（`GW004`）。ただし `notes` と `x-` で始まるキーは自由なメモとして扱います。

Graph シナリオでは、次のコマンドを使います。

```bash
szzbench validate-graph
szzbench generate-graph
szzbench verify-graph
szzbench new-graph-scenario
```

`scenario.graph.yml` は、通常の `scenario.yml` より表現力が高いスキーマです。すでに draft ではなく、バージョンは `graph-1.0` です。凍結時に満たした基準は `docs/decisions/vocabulary.md` の §4 に記録しています。Graph シナリオは `schema_version: "graph-1.0"`、通常のシナリオは `schema_version: "1.0"` を引用符付きで書きます。ほかの値は `validate-graph` と `validate` がエラーにします（GE002、E004、E010）。

### シナリオスキーマの境界方針

`scenario.yml` は、`main` 上の線形履歴と単純なファイル操作、単純な commit-level exact-set oracle で表現できる、制限された部分集合のシナリオに使います。

実際には、次のすべてが成り立つときに `scenario.yml` が適切です。

- 履歴が `main` 上の単一の線形チェーンである
- コミットの親が暗黙である、または各コミットが直前のコミットだけに依存する
- 操作が `write_file` と `replace` に限られる
- 1 つのコミットが複数の操作を含んでよい
- 期待される答えが commit-level の exact set であり続ける限り、1 つのバグに複数の BIC があってよい
- 各バグの BFC は 1 つである

グラフ固有の履歴、関係メタデータ、特殊な操作、高度な評価セマンティクスが必要なシナリオには `scenario.graph.yml` を使います。次のものが含まれます。

- 明示的な DAG 履歴、branch、merge コミット、squash merge、release branch、cherry-pick、backport
- 通常の部分集合の外にある操作（rename、move、copy、delete、バイナリ書き込み、chmod、生成ファイル操作、エンティティの移動/コピー、commit generator、patch-from/squash 操作など）
- work item、issue、developer hint、clone/copy 関係、bug instance、origin fault、direct/origin BIC 関係、リファクタリングのメタデータ
- 主要な評価単位としての複数 BFC、または複数の独立したバグ
- 評価 variant、top-k 評価、部分的または緩和されたクレジット、acceptable related コミット、related-but-not-correct コミット、line/entity/branch/work-item/bug-level の評価ポリシー

要するに、`scenario.yml` は `scenario.graph.yml` の制限された部分集合として扱います。すなわち、`main` の線形履歴と単純な commit-level exact-set oracle です。グラフ構造やより豊かな評価メタデータを必要とするものはすべて `scenario.graph.yml` に置きます。

### このベンチマークが検証しないもの

`szzbench baselines` は、宣言された安価な予測器の族（メタデータのみ、履歴上の位置のみ、ファイル接触の形、古典的な blame ベースライン）を通常の evaluator で採点します。そのため、SZZBench 上のあらゆる結果は床（floor）と比べて読めます。279 シナリオの出荷スイートでの計測結果：**ファイルを一つも開かない「履歴の 2 番目のコミットを報告する」規則が 160/279 を解き、古典的な `blame-deleted-lines` ベースラインの 156/279 を 4 件上回ります**。両者の優劣は、新しいシナリオのバッチごとに入れ替わっています。何らかの安価な規則が 279 シナリオのうち 233 を解きますが、これは oracle を知っている前提の上界であり、攻撃者のスコアではありません。届かない 46 件はすべて複数コミットの oracle を持ちます。これは選択ではなく強制された性質で、答えが 1 コミットなら必ずいずれかの位置規則が、空なら `abstain` がそれを名指します。メタデータ族は偶然の水準にあり、これは下記の漏洩保証が成り立っていることを意味します。

すべてのシナリオは `meta.tier` を宣言します。**233 件が `control`** で、手法が特定の入力条件を扱えることを確認するものであり、安価な規則が解けても構いません。**46 件が `discriminating`** で、宣言されたどの安価なベースラインも解けません。そのうち 34 件は一つの軸に対して設計されたもので、答えは 2 コミットであり、修正が削除した行を blame しても片方には到達しません。別の形で安価な規則を破るものが 5 件あります。SZZ-0218 と SZZ-0220 は答えのすべてに blame が到達する一方、blame が*付け加える*コミットによって失敗し、SZZ-0222 は blame の答えに必要コミットが一つも含まれず、SZZG-0148 と SZZG-0149 は 3 コミットを答えとし、2 件という閾値に届きません。残る 7 件はこの tier のために設計されたものではなく、既存のシナリオのうち結果としてどの安価な規則にも解かれなかったものです。17 カテゴリすべてが 2 件以上を持つため、単一の履歴に過適合してカテゴリを通過することはできません。control が安価に解けることは欠陥ではありません。tier が防ぐのは、control を「手法が識別力を持つ証拠」として読むことです。

`szzbench coverage` は対になるコマンドです。各シナリオの oracle のサイズ、バグ混入コミットの深さ、fault ファイルに触れる distractor の数、履歴の大きさと分岐の多さ、そして素朴な blame が oracle をどう扱うか（`blame_class`）を計測し、形状の次元がすべて一致するシナリオをグループ化します。また、宣言された各 fault statement を共有するシナリオ数を、全体とカテゴリごとに報告します（issue #13）。

このベンチマーク上の数字を報告・比較する前に [docs/baselines.md](docs/baselines.md) を読んでください。この床を引き上げる作業は issue #13、#14、#35 で追跡しています。

### 生成リポジトリが明かさないもの

ツールには生成リポジトリとバグ修正コミットが与えられます。そのリポジトリの中に、コミットの oracle 上の役割を示すものは何もありません。コミットメッセージは作者の視点から変更を説明し、シナリオ id、役割を表す語、操作の一覧を決して含みません。作者と日付はシナリオ id とコミットの番号から導かれ、役割からは導かれません。どのファイル内容もパスも、どのコミットが答えかを述べません。バグ修正コミットは自然な修正の文言を保ちます。BFC は答えの一部ではなく、SZZ への入力だからです。

また、バグ修正コミットが HEAD の履歴にあるとは限りません。`generate` は既定ブランチをチェックアウトした状態で終わりますが、`generate-graph` は HEAD をシナリオの最後のコミットのブランチに残し、それは既定ブランチ以外のブランチのこともあります。SZZG-0054 は `release` で終わり、`main` にある唯一のバグ修正コミットは HEAD から到達できません。SZZG-0075 のように、バグ修正コミットが一度もマージされないブランチに残ることもあります。そのため、ツールは HEAD から履歴をたどるのではなく、与えられたバグ修正コミットから始めるか、すべての ref をたどってください（`git log --all`）。`metadata/graph-map.json` は HEAD の位置を記録します（`head`）。規則は `docs/generator-options.md` §3 にあります。

シナリオ id、タイトル、リポジトリの生成先ディレクトリはシナリオを説明しますし、修正は当然、何を直したかを名指しします。意図的に隠していないものや、予測がコミットをどう名指しできるか（`evaluate --reference-format`）を含む完全な方針は [docs/decisions/oracle-leakage.md](docs/decisions/oracle-leakage.md) にあり、`validate --lint` と `tests/test_no_oracle_leakage.py` が検査します。

## ディレクトリ構成

Git で管理している最上位のファイルとディレクトリは以下のとおりです。`src/szzbench/` はすべてのモジュールを示します。

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

主な役割は以下です。

| パス | 役割 |
|---|---|
| `src/szzbench/` | Python 実装本体。CLI、シナリオの種類ごとの validator・generator・verifier・雛形の作成、スイート全体の生成・index の検査・シナリオ README のヘッダの生成を行うモジュール、evaluator・baselines・coverage、共通の補助モジュール。 |
| `scenarios/` | 通常シナリオ `SZZ-XXXX` を管理する場所。 |
| `advanced-scenarios/` | Graph シナリオ `SZZG-XXXX` を管理する場所。 |
| `docs/` | 参照用の文書。検査コード、生成のオプション、評価ポリシー、ベースライン、シナリオ README のヘッダ、廃番になったシナリオ ID。`docs/decisions/` には、その背後にある設計上の決定を記録しています。 |
| `examples/` | 第三者の SZZ 実装を同梱スイートで実行した記録。実行ごとに予測と評価レポートがあります。 |
| `generated-input-repos/` | generator が生成する Git リポジトリの出力先。Git 管理対象外。 |
| `tools/adapters/` | SZZ ツール固有の出力を SZZBench predictions 形式へ変換するサンプル adapter。 |
| `tools/scenario-editor/` | 通常シナリオを作成するためのローカル Web アプリ。 |
| `tools/generated-repo-viewer/` | 生成済み Git リポジトリを確認するためのローカル Web アプリ。 |
| `tests/` | テストコード。テストに必要なものは `tests/README.md` にあります。 |
| `.github/workflows/` | CI。 |
| `LICENSES.md` | どのファイルにどのライセンスが適用されるか。ソフトウェアには MIT License（`LICENSE-MIT`）、シナリオと文書には CC BY 4.0（`LICENSE-CC-BY-4.0`）。 |

## インストール

Python 3.10 以上が必要です。

Git 2.29 以上も必要です。SZZBench は Git を利用者自身の Git 設定から切り離して実行するため、署名、フック、global な ignore や attributes のファイルは生成結果に影響しません（`docs/generator-options.md` §5）。JDK（`javac` と `java`）はシナリオのコードをコンパイル・実行するテストでだけ必要で、ない場合そのテストはスキップされます。Node.js は `tools/` 以下のツールでだけ必要です。

テストは CI で、Linux 上で 2 通りに実行しています（`.github/workflows/tests.yml`）。Python 3.14 と GitHub の `ubuntu-latest` ランナーの現行の Git の組み合わせと、Python 3.10 と Debian 12 の Git 2.39 の組み合わせです。開発は macOS で行っています。Windows ではテストしていません。以下の PowerShell のコマンドは参考として載せています（[#109](https://github.com/higolab/SZZBench/issues/109)）。

SZZBench のルートディレクトリで、仮想環境を作成して有効化します。

macOS / Linux の場合:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell の場合:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

その後、SZZBench をインストールします。

```bash
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev]"
```

`-e` は editable install の意味です。開発中のソースコードを直接参照するため、`src/szzbench/` 以下を修正した場合でも、基本的には再インストールせずに変更が反映されます。

開発用依存関係が不要な場合は、`dev` extra なしでインストールします。

```bash
python -m pip install -e .
```

インストール後、次のように `szzbench` コマンドが使えます。

```bash
szzbench --help
```

後でこのプロジェクトで作業するときは、`szzbench`、`pytest`、その他のプロジェクト用コマンドを実行する前に、再度仮想環境を有効化します。

macOS / Linux の場合:

```bash
source .venv/bin/activate
```

Windows PowerShell の場合:

```powershell
.\.venv\Scripts\Activate.ps1
```

## 通常シナリオの使い方

### validate

`scenario.yml` の構造や参照関係を検査します。

```bash
szzbench validate scenarios/SZZ-0006/scenario.yml
```

operation をメモリ上でシミュレーションして検査したい場合は、`--simulate` を使います。

```bash
szzbench validate --simulate scenarios/SZZ-0006/scenario.yml
```

warning も失敗扱いにしたい場合は、`--strict` を使います。

```bash
szzbench validate --simulate --strict scenarios/SZZ-0006/scenario.yml
```

JSON で出力したい場合は、`--json` を使います。

```bash
szzbench validate --simulate --json scenarios/SZZ-0006/scenario.yml
```

任意の lint もあわせて実行するには、`--lint` を使います。lint は、中立なコミットメッセージ、統制語彙、生成された README ヘッダなど、よいシナリオの条件を検査します（`docs/validation.md`）。`--lint` は `--simulate` を含みます。

```bash
szzbench validate --lint --strict scenarios/SZZ-0006/scenario.yml
```

### generate

`scenario.yml` から実際の Git リポジトリを生成します。

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force
```

`--no-verify` を付けると、生成後の verify をスキップします。

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force   --no-verify
```

verify でエラーが見つかると、`generate` は `[ERROR] GENERATION_FAILED: Generated repository failed verification.` に続けてその所見を表示し、終了コード 1 で終わります。出力には `metadata/verify-result.json`、`generation.log`、`generation-error.json` が残り、`manifest.json` は書かれないので、`generate-all-repos` はその出力を生成し直します。

verify の警告（基本の blame が期待する BIC に届かないことを示す `W703` など）は表示されるだけで、終了コードは 0 のままです。`--strict` を付けると、`verify --strict` と同じく警告があれば終了コード 1 で終わります。どちらの場合も出力は完全で、そのまま残ります。`--strict` と `--no-verify` は同時に指定できません。`--json` を付けると、標準出力に JSON 文書を 1 つだけ出力します。中身は `kind`、`scenario`、`output_dir`、`status`（`generated` または `failed`）、`commit_count`、`error`、`verification` で、`verification` は `verify --json` が出力するもの（件数と所見）、`--no-verify` のときは `null` です。生成に失敗したときも文書を出力し、終了コード 1 で終わります。

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force   --strict   --json
```

`--force` が既存の `--out` を置き換えるのは、それが以前の生成物か、`repo/` と `metadata/` しか含まないディレクトリの場合だけです。`--out` がファイルである、それ以外のものを含む、シナリオファイルを含む、作業ディレクトリそのものかその親である、のいずれかに当たるときは、何も削除せずに拒否します。`generate-graph` と `generate-all-repos` にも同じ規則が適用されます。

生成されるディレクトリは次のような構成です。

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

生成済みリポジトリが `scenario.yml` と対応し、生成した直後の状態のままかを検査します。`commit-map.json` の全コミットが ref から辿れ、記録された author と日時を持つこと、既定ブランチが最後のコミットを指してチェックアウトされていること、index とワークツリーに変更が無いことを確かめます（[docs/validation.md](docs/validation.md) の E600–E609）。SZZ ツールが checkout やコミットをしたリポジトリは `verify` に通りませんが、全コミットが辿れる限り `evaluate` は採点します。

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml
```

必要に応じて `commit-map.json` を明示できます。

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml   --commit-map generated-input-repos/SZZ-0006/default/metadata/commit-map.json
```

`--strict` を付けると、エラーだけでなく警告（基本の blame が期待する BIC に届かないことを示す `W703` など）でも終了コード 1 で終わります。`--json` を付けると、結果を JSON で出力します。

### new-scenario

新しい通常シナリオの雛形を作成します。

```bash
szzbench new-scenario   --title "Formatting after bug introduction"   --category "Intermediate noise and history noise"   --tier control   --factor formatting-noise   --factor intermediate-history
```

デフォルトでは、次のようなディレクトリが作成され、`scenarios/index.yml` も更新されます。

```text
scenarios/SZZ-XXXX/
├── scenario.yml
└── README.md
```

新しいエントリは、index の `scenarios:` リストの末尾に、同梱のエントリと同じ書式で追加されます。index のほかの行は変わりません。編集後の index が読み込めない場合は、何も書き込まずに終了ステータス 1 で終了します。

雛形は、シナリオが持てる最小の履歴です。`c0` が `Range` クラスを書き、`c1` がその範囲の判定を狭め、`c2` が元に戻します。期待する BIC は `c1`、BFC は `c2` です。`szzbench validate --simulate --strict --lint` はこの雛形をそのまま受け付けるので、最初の実行から lint が factor とコミットメッセージを検査します。報告されることがあるのは情報の項目 `I413` だけです（生成器が `c1` に割り当てた作者が、ほかに何も書いていないとき）。履歴、バグ、checks は、そのシナリオ自身のものに置き換えてください。

`--category` は [docs/decisions/vocabulary.md](docs/decisions/vocabulary.md) の第 3 節の分類を、コード（`S3`）か名前（`Intermediate noise and history noise`）で指定します。`meta` と index のエントリには両方が入り、それ以外の値は拒否されます。`--tier` は必須で、デフォルトはありません。シナリオが何のためにあるか（`control` か `discriminating`、第 7 節）を宣言するもので、`discriminating` の雛形には、この tier が求めるとおり、すべての family を並べた `meta.defeats` も入ります。`--factor` は 1 つ以上必須です。factor の語彙は開いていますが、`--lint` が拒否する factor（スキーマのキーや操作名（`E400`）、ハイフンとアンダースコアの混在（`E402`））と、空白を含む factor は拒否されます。拒否されたときは何も書き込まず、終了ステータス 1 で終了します（argparse が拒否するオプションでは 2）。

`--difficulty` は `easy` / `medium` / `hard` のいずれか（デフォルトは `medium`）で、リポジトリ生成後に `szzbench coverage` が計測した床と照合します。slug（`meta.slug`、index のエントリ、リポジトリ名に入ります）はタイトルから作られ、`--slug` で指定することもできます。`--status` は `meta.status` を `draft`（デフォルト）か `active` に設定します。`retired` は削除されたシナリオのための値です（[docs/retired-ids.md](docs/retired-ids.md)）。`--root` は `scenarios/` 以外のスイートのルートにシナリオを作って、そのルートの `index.yml` を更新します。

## Graph シナリオの使い方

### validate-graph

`scenario.graph.yml` の構造や参照関係を検査します。

```bash
szzbench validate-graph advanced-scenarios/SZZG-0001/scenario.graph.yml
```

Graph operation をシミュレーションして確認したい場合は、`--simulate` を使います。operation は基本的にメモリ上で再生しますが、生成時に Git が内容を計算するコミット（merge、実際の cherry-pick や revert、patch 系の operation、衝突解決）を含むシナリオは、代わりに一時ディレクトリで Git を使って実際に生成して確認します（`docs/validation.md`）。

```bash
szzbench validate-graph   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

より厳密な path / entity 形状の検査を行う場合は、`--strict-paths` を使います。

```bash
szzbench validate-graph   --strict-paths   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

`--strict`、`--lint`、`--json` は `validate` と同じように働きます。Graph の lint は静的な検査なので、ここでは `--lint` は `--simulate` を含みません。また、lint はエラーが見つからなかったときにだけ実行されます。

### generate-graph

`scenario.graph.yml` から実際の Git リポジトリを生成します。

```bash
szzbench generate-graph   advanced-scenarios/SZZG-0001/scenario.graph.yml   --out generated-input-repos/SZZG-0001/default   --force
```

生成されるディレクトリは次のような構成です。

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

`commit-map.json` は、論理コミット ID と実際の Git hash の対応を記録します。

`graph-map.json` は、Graph シナリオ向けの追加情報を記録します。branch、parent、role などの情報を含みます。コミットの `parents` と `parent_hashes` は、シナリオで宣言された親です。`commit_generator` 操作を持つコミットでは、Git 上の第一親は最後の生成コミットで、それは `generated_commits` に並んでいます（`docs/generator-options.md` §2）。`head` は、生成が HEAD を残した位置を記録します。`branch` は HEAD のあるブランチ（HEAD が detached のときは null）、`hash` はそのコミットです。HEAD はシナリオの最後のコミットのブランチに残り、それは既定ブランチとは限りません（「生成リポジトリが明かさないもの」と `docs/generator-options.md` §3 を参照）。

verify でエラーが見つかったときの表示と記録は、`generate` と同じです。`--no-verify`、`--strict`、`--json` も `generate` と同じように働きます（`kind` は `graph`）。

### verify-graph

生成済みリポジトリが `scenario.graph.yml` と対応しているかを検査します。コミットとバグの位置に加えて、リポジトリが生成直後の状態のままか（`graph-map.json` が記録するブランチとタグ、HEAD、index とワークツリーに変更がないか）も検査します。そのため、SZZ ツールがチェックアウト・コミット・ブランチ作成をしたリポジトリは検証に失敗します。一方、`generate-all-repos` と `evaluate` の古さの判定は、こうした変更を許します（`docs/generator-options.md` §6）。

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml
```

必要に応じて `commit-map.json` と `graph-map.json` を明示できます。

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml   --commit-map generated-input-repos/SZZG-0001/default/metadata/commit-map.json   --graph-map generated-input-repos/SZZG-0001/default/metadata/graph-map.json
```

`--strict` と `--json` は `verify` と同じように働きます。

### new-graph-scenario

新しい Graph シナリオの雛形を作成します。

```bash
szzbench new-graph-scenario   --title "BIC on feature branch and BFC on main"   --category G4   --tier control   --factor branch-merge
```

`--difficulty` は `easy` / `medium` / `hard` のいずれか（デフォルトは `medium`、`advanced` は廃止）で、Classic スイートと同じく、リポジトリ生成後に `szzbench coverage` が計測した床と照合します（[docs/decisions/vocabulary.md](docs/decisions/vocabulary.md) の第 4 節）。

デフォルトでは、次のようなディレクトリが作成され、`advanced-scenarios/index.yml` も更新されます。

```text
advanced-scenarios/SZZG-XXXX/
├── scenario.graph.yml
└── README.md
```

`new-scenario` と同じく、エントリは `scenarios:` リストの末尾に、2 つの index に共通の形で追加され（issue #200）、編集後の index が読み込めない場合は何も書き込みません。

`--category`、`--tier`、`--factor`、`--slug`、`--status`、`--root` は `new-scenario` と同じように働きます。デフォルトのルートは `advanced-scenarios/` です。拒否された factor は Graph のコード（`GE400`、`GE402`）で示されます。Graph の index のエントリも、classic と同じキー（`slug` と `readme` を含む）を持ちます。雛形は同じ 3 つのコミットを `main` に持ち、README の `## Expected history` ブロックはそのコミットから作られるので、`szzbench validate-graph --simulate --strict --strict-paths --lint` はこの雛形をそのまま受け付けます。報告されることがあるのは `GI413` だけです。

## validate-index

`scenarios/index.yml` と `advanced-scenarios/index.yml` を、シナリオのディレクトリと照合します。すべてのシナリオディレクトリにエントリがあり、すべてのエントリにシナリオファイルと README があること、廃番の ID を使うエントリがないこと、エントリがシナリオの `meta` から写しているフィールド（タイトル、status、factors など）がすべてそろい、今もシナリオと一致することを確かめます。2 つの index は同じ形で、最上位は `scenarios:` だけ、どのエントリも同じ 10 個のキーを持ちます（issue #200）。index はこれらのフィールドを繰り返し持つため、以前はそこがずれていました（issue #19）。

```bash
szzbench validate-index
szzbench validate-index --json
```

エラーが 1 件でもあれば終了コード 1 で終わります。検査コード IE001–IE047 は [docs/validation.md](docs/validation.md) にあります。`--scenarios-root` と `--advanced-scenarios-root` を付けると、`scenarios/` と `advanced-scenarios/` 以外のスイートのルートの index を検査します。`--json` を付けると、結果を JSON で出力します。`new-scenario`、`new-graph-scenario`、Scenario editor は自分でエントリを追加するので、このコマンドは主に手で編集したときの確認に使います。

## evaluate

SZZ ツールの予測結果を、SZZBench の commit-level oracle と照合して評価します。

```bash
szzbench evaluate \
  --predictions predictions.jsonl \
  --generated-root generated-input-repos \
  --include-generated \
  --evaluation-variant origin-aware \
  --out generated-szz-results/my-tool
```

`--predictions` は JSON または JSONL を受け取ります。共通 prediction 形式は、予測が空のシナリオも表現できるように、シナリオ単位のレコードを書けます。

```jsonl
{"scenario_id":"SZZ-0047","predictions":[]}
{"scenario_id":"SZZ-0006","predictions":[{"fix_commit":"<actual hash>","inducing_commit":"<actual hash>"}]}
```

予測 BIC ごとに 1 レコードを書く形式も使えます。

```jsonl
{"scenario_id":"SZZ-0006","fix_commit":"<actual hash>","inducing_commit":"<actual hash>"}
```

評価に必須なのは `scenario_id` と `inducing_commit` です。`fix_commit` は任意ですが、bug-fixing commit を複数持つシナリオは fix ごとにも採点されます。予測は `fix_commit` が指す fix の答えとして数えられ、`fix_commit` のない予測はすべての fix の答えとして数えられます（`docs/evaluation-policies.md` §1.7）。`inducing_commit` には実 Git hash、ユニークな hash prefix、または `commit-map.json` の論理 commit id を指定できます。hash と prefix は大文字でも小文字でもよく、参照の前後の空白（末尾の改行など）は無視されます。論理 commit id は `commit-map.json` のとおりに書きます。どのコミットにも解決できない参照はシナリオを FAIL にし、`unknown_predictions` に記録され、precision では false positive として数えられます。

レコードでは、ツールがそのシナリオで失敗したことも表せます。その場合、レコードの予測内容にかかわらずシナリオは FAIL になります（`docs/evaluation-policies.md` §1.6）。

```jsonl
{"scenario_id":"SZZ-0006","status":"error","errors":["<what went wrong>"],"predictions":[]}
```

アダプタは、ツールを実行した生成済みリポジトリの識別子 `repository_id` も書きます。同じシナリオの別の生成物に対して作られたレコードは stale として FAIL になります。

読めないレコードは読み込みエラーです。リストでない `predictions`（`null` を含む）、`inducing_commit` がない予測、または `inducing_commit` が空でない文字列ではない予測、型の誤った `rank`・`fix_commit`・`status`・`repository_id`、`predictions` のリストとトップレベルの `inducing_commit` の両方を持つレコードがこれに当たります。このとき `evaluate` は終了コード 1 で終わり、レコードが指すシナリオは、ほかのレコードの予測内容にかかわらず `run_status: invalid` として FAIL になります（`docs/evaluation-policies.md` §1.6）。Issue #138 までは、予測を読めなかったレコードも空の答えとして採点され、`expect_no_bic` のシナリオで PASS していました。

`--generated-root` 以下の生成済みリポジトリをすべて評価するには `--include-generated` を使います。このとき、どのレコードにも現れないシナリオは、棄権ではなく記録の欠落（`run_status: missing`）として FAIL になります。ツールが実行されて何も見つけなかったシナリオには、上の `SZZ-0047` のような空のレコードを書いてください。`tools/adapters/` のアダプタはそのようなレコードを書きます。

`evaluate` は、レポートにエラー（読み込みエラーや古い生成物など）があれば終了コード 1、なければ、FAIL のシナリオがいくつあっても 0 で終わります。`--fail-on-non-pass` を付けると、PASS でないシナリオが 1 件でもあるときにも終了コード 1 で終わります（`docs/evaluation-policies.md` §1.6）。

空の予測ファイルや、出力の無い `--generated-root` に対する実行のように、1 件も採点しなかった実行は、`--fail-on-non-pass` の有無にかかわらずエラー（`EVALUATE_FAILED`、終了コード 1）になります。`--include-generated` は存在しない `--generated-root` を拒否します（issue #141）。

Graph scenario では、`--evaluation-variant` で `expected_szz.evaluation_variants` に定義された `direct-only`、`origin-aware`、`relaxed-with-credit` などの評価 variant を選べます。省略した場合は、シナリオに `default_variant` があればそれを使い、なければ `expected_szz.commit_level` を使います。指定した名前の variant を定義していないシナリオは、オプションを省略したときと同じ oracle で採点され、使った oracle が注記されます。そうしたシナリオは、実行全体で 1 件の警告にまとめて報告されます。空の名前はオプションの省略と同じです。classic scenario には variant がなく、そのことは実行ごとに 1 回だけ表示されます（`docs/evaluation-policies.md` §1.3）。variant 名の照合ではハイフンとアンダースコアの違いを吸収します。このオプションは、生成リポジトリのディレクトリを選ぶ `--variant` とは別物です。

JSON レポートには従来の `true_positives`、`false_positives`、`false_negatives` と、シナリオごとの `unknown_predictions`、`run_status`、`run_errors` に加えて、Graph scenario 用の `evaluation_policy`、`evaluation_variant`、`hard_false_positives`、`related_origin_hits`、`related_but_not_correct_hits`、`acceptable_related_hits`、`weighted_credit`、`minimum_required_met`、`top_k` も出力されます。

`--json` を付けると、集計の代わりにこのレポートを標準出力に出力します。`--out` はこれを `evaluation-results.json` に書き出し、同じ場所に `evaluation-results.md` も書きます。シナリオファイルが `scenarios/` と `advanced-scenarios/` 以下にない場合は、`--scenarios-root` と `--advanced-scenarios-root` でその場所を指定します。`--reference-format` は、予測がコミットを名指す書き方を制限します。`hash` は hash と hash prefix だけを受け付け（リポジトリを読むツールが出せるのはこれだけです）、`logical` は `c1` のような論理 commit id だけを受け付け（adapter とテストの fixture 向け）、デフォルトの `auto` は両方を受け付けます。受け付けなかった参照は unknown prediction になります（`docs/decisions/oracle-leakage.md`）。

ツールは、生成リポジトリの上でバグ修正コミットから実行します。`tools/adapters/` の adapter は、バグ修正コミットをシナリオと `metadata/commit-map.json` から読み取り、その hash をツールに渡します。そうせずに HEAD から履歴をたどるツール（`--all` なしで `git log` を実行するものなど）は、Graph シナリオのバグ修正コミットを見落とすことがあります。`generate-graph` は HEAD をシナリオの最後のコミットのブランチに残し、そのブランチがバグ修正コミットを含むとは限らないからです（「生成リポジトリが明かさないもの」を参照。`metadata/graph-map.json` は HEAD を `head` として記録します）。

SZZ Unleashed は、adapter がツールの実行まで行います。jar をビルドし（[examples/szz-unleashed-run/README.md](examples/szz-unleashed-run/README.md)）、`--jar` で渡してください。`--depth` は SZZ Unleashed の `-d`（行の対応グラフの深さ。既定値は SZZ Unleashed 自身と同じ 3）で、結果を大きく左右します。上の README には深さ 3 と深さ 1 の実行記録があります。`--jar` を付けない場合、adapter は以前の実行が `generated-input-repos/<SCENARIO_ID>/default/szz-unleashed/run-depth<depth>/` に残した `fix_and_introducers_pairs.json` を変換するだけです。

```bash
tools/adapters/szz_unleashed_to_predictions.py \
  --jar /path/to/szz_find_bug_introducers-0.1.jar \
  --generated-root generated-input-repos \
  --out generated-szz-results/szz-unleashed/predictions.jsonl
```

PyDriller の場合は、生成済みリポジトリに adapter を適用します。

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

PySZZ の B-, AG-, MA-, L-, R-SZZ は、`tools/adapters/pyszz_variants_to_predictions.py` が PySZZ 自体を実行し、変種ごとに予測ファイルを書きます。インストールするもの（PySZZ の結果を左右するライブラリのバージョンと srcML を含む）と、同梱スイートで5つを実行した記録は [examples/pyszz-run/README.md](examples/pyszz-run/README.md) にあります。

トークン単位の履歴に対する B-SZZ は、`tools/adapters/token_bszz_to_predictions.py` が実行します。`tools/adapters/token-bszz/` から作る Docker イメージの中で、生成済みリポジトリを cregit で1行1トークンに書き換え、書き換えたコピーに PySZZ の B-SZZ を実行し、答えを元のリポジトリのコミットで表します。インストールするものと、同梱スイートでの実行記録は [examples/token-bszz-run/README.md](examples/token-bszz-run/README.md) にあります。

## baselines

宣言された安価な予測器の族を生成済みリポジトリに適用し、通常の evaluator で採点します。上の「このベンチマークが検証しないもの」で説明した床です。族の内容と同梱スイートでの計測結果は [docs/baselines.md](docs/baselines.md) にあります。

```bash
szzbench baselines --out results/floor
szzbench baselines --family position --family blame
```

`--family` は指定した族（`metadata`、`position`、`shape`、`blame`）だけを実行し、繰り返し指定できます。デフォルトは 4 つすべてです。こうして絞った実行では、どの安価な規則も解けない `control` シナリオがどれかは判定しません。`--out` はディレクトリに `baselines.json` と `baselines.md` を書き出し、`--json` はレポートを JSON で出力します。`--generated-root` と `--variant` で生成済みリポジトリを、`--scenarios-root` と `--advanced-scenarios-root` でシナリオファイルを、`evaluate` と同じように選びます。古い出力は採点せずにエラーとして報告し、エラーが 1 件でもあれば終了コード 1 で終わります。

## coverage

上の「このベンチマークが検証しないもの」で説明したとおり、各シナリオが何に寄与しているかを計測します。oracle のサイズ、バグ混入コミットの深さ、distractor、履歴の大きさと分岐の多さ、`blame_class` を計測し、形状が一致するシナリオをグループ化します（[docs/baselines.md](docs/baselines.md)）。

```bash
szzbench coverage --out results/coverage
```

`--out` はディレクトリに `coverage.json` と `coverage.md` を書き出します。`--json`、`--generated-root`、`--variant`、`--scenarios-root`、`--advanced-scenarios-root` と終了コードは `baselines` と同じです。

## generate-all-repos

`scenarios/` 以下の通常シナリオと、`advanced-scenarios/` 以下の Graph シナリオから、まとめてリポジトリを生成します。

```bash
szzbench generate-all-repos
```

このコマンドは、次のファイルを走査します。

- `scenarios/*/scenario.yml`
- `advanced-scenarios/*/scenario.graph.yml`

各リポジトリは `generated-input-repos/<SCENARIO_ID>/default/` 以下に生成されます。`--scenarios-root` と `--advanced-scenarios-root` を付けるとほかのスイートのルートを走査し、`--out-root` を付けると `generated-input-repos/` 以外のルートの下に書き出します。デフォルトと同じく、どれも作業ディレクトリからの相対パスです。読むのは各ルートの直下にあるシナリオのディレクトリだけです。2 つのルートに同じ id がある場合（大文字小文字の違いは同じとみなします。大文字小文字を区別しないファイルシステムでは出力が 1 つになるためです）や、`--out-root` がシナリオのルートそのもの、またはその中にある場合は、何も書き出す前に止まります（issue #168）。

生成は最後に `metadata/manifest.json` を書き出します。ここには、シナリオファイルのハッシュ、生成器のコードの指紋、予測の記録が持つリポジトリの識別子が記録されます。既存の出力は、この manifest が今も一致し、manifest が記述するものがすべて残っている場合にだけスキップされます。manifest がない出力（中断した生成や、2026-09-29 より前に作られたもの）、manifest を読めない・解析できない出力（理由にその訳を示します）、その後シナリオファイルや生成器のコードが変わった出力、manifest が記述するもの（リポジトリ、そのコミット、commit map、シナリオのコピーなど）の一部を失った出力は「古い」とみなされ、理由を表示して作り直されます（`docs/generator-options.md` §6）。そのため繰り返し実行しても安全で、すべての出力を最新にし、最新のものには手を付けません。`evaluate`、`baselines`、`coverage` は古い出力を採点しません。

既存の生成済みリポジトリを削除して作り直す場合は、`--overwrite` を使います。

```bash
szzbench generate-all-repos --overwrite
```

`--overwrite` は、出力が最新でも各シナリオを生成し直します。生成は、古い出力の作り直しも含めて、いつも `generated-input-repos/<SCENARIO_ID>/default.tmp/` に書き出し、生成と verify が通ってから `default/` と差し替えます。旧出力は `default.old/` に退避し、新しい出力を置いた後で削除します（issue #168）。

あるシナリオの生成に失敗しても実行は止まりません。そのシナリオはエラーとともに `Failed` として表示され、コマンドは次のシナリオに進み、最後に集計を表示して終了コード 1 で終わります。生成のエラーではない例外（SZZBench 内部のクラッシュ）は、トレースバックも表示します。生成後の verify で失敗したシナリオは、verify のエラーも表示します。旧出力があればそのまま残し、失敗した試行のファイル（`generation.log`、`generation-error.json`、verify に失敗した場合は `metadata/verify-result.json`）は `<SCENARIO_ID>/default.tmp/` に残します。その場所は `Failed` の行に表示します。差し替えの後で `default.old/` を削除できなかった場合は警告として表示し（`SZZ-0005: [WARNING] the previous output, moved aside to …`）、次の実行で削除します。

生成後の検証をまとめてスキップする場合は、`--no-verify` を使います。

```bash
szzbench generate-all-repos --no-verify
```

各出力の verify の警告は、1 件 1 行で、シナリオ ID に続けて標準エラーに表示します（`SZZ-0078: [WARNING] W703: ...`）。集計では、警告のある出力の数を `Warned` として示します。最新としてスキップした出力については、その生成が `metadata/verify-result.json` に記録した verify の結果を報告します。読める `verify-result.json` がない出力は生成し直します。`--strict` を付けると、どれかの出力の verify に警告があれば終了コード 1 で終わります（`--no-verify` とは同時に指定できません）。`--json` を付けると、標準出力に JSON 文書を 1 つだけ出力します。中身は `items`（シナリオごとに 1 つで、`generate --json` のキーに `scenario_id`、`overwritten`、`stale_reason`、`traceback`、`leftover`（残った `default.old/` についての警告、または `null`）を加えたもの）、`orphans`、テキストの集計と同じ件数を持つ `summary` です。

```bash
szzbench generate-all-repos --strict
szzbench generate-all-repos --json
```

## readme

各シナリオの README が、シナリオファイルから生成したヘッダで始まっているかを確認し、必要なら再生成します。

```bash
szzbench readme
szzbench readme scenarios
```

ヘッダ（タイトル、カテゴリ、tier、status、difficulty、言語、factors、evaluator が解決するオラクル、Graph シナリオでは使用している graph 専用機能）は、README のうちツールが書く唯一の部分です。ヘッダより後の本文は作者のものであり、ツールは触りません。ヘッダが無い、またはシナリオと一致しない README があると `szzbench readme` は終了コード 1 を返し、`validate --lint` / `validate-graph --lint` も同じ不一致を `W455` / `GW455` として報告します。スイートのルート（`scenarios`、`advanced-scenarios`）、シナリオのディレクトリ、シナリオファイルを指定すると、検査はそれらのシナリオに限られます。どのシナリオファイルにも当たらない指定はエラー（終了コード 1）になります（issue #188）。指定がなければ、`--scenarios-root` と `--advanced-scenarios-root`（デフォルトは `scenarios` と `advanced-scenarios`）以下のシナリオを検査します。`--json` を付けると、レポートを JSON で出力します。

```bash
szzbench readme --write
szzbench readme --write advanced-scenarios/SZZG-0022
```

`--write` は、両スイート全体、またはコマンドラインで指定したシナリオについて、古い・形の崩れた・欠けているヘッダを再生成します。生成された形から崩れたヘッダは丸ごと置き換えるので、ヘッダは 1 つだけ残ります。README の BOM と CRLF の改行はそのまま保ちます。`--write` は書いた結果を検査し直し、まだ古い README があれば終了コード 1 を返します。詳細は [docs/scenario-readme.md](docs/scenario-readme.md) を参照してください。

## clean

`generated-input-repos/` 以下の生成済みリポジトリを削除します。

```bash
szzbench clean
```

削除対象を確認するだけなら、`--dry-run` を使います。

```bash
szzbench clean --dry-run
```

対象ルートを明示することもできます。

```bash
szzbench clean --root generated-input-repos
```

`clean` は通常シナリオと Graph シナリオの両方の生成物に使えます。

`clean` はルート以下にある生成物を、深さに関係なくすべて削除します。そのため、ファイルシステムのルート、ホームディレクトリ、作業ディレクトリそのものかその親をルートに指定すると、何も走査せずに拒否します。作業ディレクトリの `generated-input-repos` 以外のルートでは、見つけた生成物を標準エラーに一覧表示し、削除してよいかを尋ねます。`--yes` を付けると尋ねずに削除します。スクリプトの中など標準入力が端末でないときは、`--yes` がなければ何も削除せずに拒否します。`--dry-run` は尋ねません。`--json` を付けると、`root`、`dry_run`、`outputs`、`summary`（`found` と `removed`）を持つ JSON 文書を標準出力に 1 つ出力します。

```bash
szzbench clean --root /tmp/szzbench-repos --dry-run
szzbench clean --root /tmp/szzbench-repos --yes --json
```

## 補助ツール

### Scenario editor

`tools/scenario-editor/` は、通常シナリオ `scenario.yml` を作成するためのローカル Web アプリです。

```bash
cd tools/scenario-editor
npm ci
npm run dev
```

ブラウザで次を開きます。

```text
http://127.0.0.1:5173
```

この editor は、メタデータ、ソースコードの各バージョン、BIC / BFC 情報を入力し、`scenario.yml` と `README.md` を作成できます。ローカル Node.js API を通じて、`scenarios/SZZ-XXXX/` 以下へ直接保存することもできます。保存には `meta.tier` の指定が必要で、保存前に `szzbench validate --lint` で検査し（エラーがあれば保存しません）、README の生成ヘッダを挿入します。バックエンドには SZZBench の依存パッケージが入った Python が必要です（`tools/scenario-editor/README.md`）。

現状では、主に通常シナリオ向けです。Graph シナリオの編集には対応していません。

### Generated repository viewer

`tools/generated-repo-viewer/` は、生成済み Git リポジトリを確認するためのローカル Web アプリです。

```bash
cd tools/generated-repo-viewer
npm ci
npm run dev
```

ブラウザで次を開きます。

```text
http://127.0.0.1:5174
```

この viewer は、`generated-input-repos/` 以下の実際の Git リポジトリを読み、Node.js backend 経由で `git log`、`git show`、`git diff`、`git blame` などを実行して表示します。

主に以下を確認できます。

- 生成済みリポジトリ一覧
- scenario metadata
- logical commit ID と Git hash の対応
- commit timeline
- 各 commit 時点のファイル一覧
- ファイル内容
- diff
- blame
- bug oracle
- `verify-result.json`
- `validation-result.json`
- `generation.log`

## テスト

開発用依存関係を入れている場合、次でテストを実行できます。

```bash
pytest
```

特定のテストだけ実行する場合は、例えば次のようにします。

```bash
pytest tests/test_generator_smoke.py
```

テストに必要なもの（JDK、Scenario Editor のテスト用の Node.js）と共通の補助関数の置き場所は [tests/README.md](tests/README.md) にあります。同じテストは、`main` への push のたびに CI でも実行され、CI は `tools/` 以下の二つの web ツールのビルドも確かめます。pull request 時の CI は一時停止しています。再開方法は [tests/README.md](tests/README.md) に記載しています。

## Git 管理しないもの

以下は Git 管理しない方針です。

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

JavaScript/TypeScript ツールの依存ライブラリは `node_modules/` に入りますが、これは Git 管理しません。必要な場合は、各 tool ディレクトリで `npm ci` を実行して再作成します。`npm ci` は `package-lock.json` に記録された版をインストールし、そのファイルを書き換えません。

Python の仮想環境 `.venv/` も Git 管理しません。必要な場合は、各環境で作り直します。

## 配布用 ZIP の作成

Git 管理下のファイルだけを ZIP にしたい場合は、次を使います。

```bash
git archive --format=zip --prefix=SZZBench/ --output=SZZBench_source.zip HEAD
```

これにより、`node_modules/`、`.venv/`、`generated-input-repos/` などの Git 管理外ファイルを含まない ZIP を作成できます。

## 現在の注意点

- `scenario.graph.yml` は通常の `scenario.yml` より表現力が高く、スキーマは draft ではなくバージョン `graph-1.0` です（`docs/decisions/vocabulary.md` §4）。
- Graph シナリオでは、履歴構造や oracle が複雑なため、`validate-graph --simulate` と `verify-graph` の両方で確認することを推奨します。
- 生成されたリポジトリは派生物なので、基本的には Git 管理しません。
- SZZBench は、実プロジェクト由来の大規模 oracle を置き換えるものではありません。SZZ の failure mode を小さく制御された履歴で確認するための補助的なベンチマークです。

## 著者とライセンス

SZZBench は、Yoshiki Higo と Inase Kondo（大阪大学）、Masanari Kondo と Yasutaka Kamei（九州大学）が開発しています。

ソフトウェア（`src/`、`tests/`、`tools/` のコード）は MIT License（[`LICENSE-MIT`](LICENSE-MIT)）、シナリオ・例・文書は CC BY 4.0（[`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0)）で提供します。どのファイルにどちらのライセンスが適用されるかと、CC BY 4.0 の素材を利用するときの帰属表示（"The SZZBench authors, *SZZBench*, https://github.com/higolab/SZZBench"）は [`LICENSES.md`](LICENSES.md) にあります。
