# SZZBench

SZZBench is a tool for generating and verifying synthetic Git repositories for evaluating SZZ techniques.

In SZZ, a tool starts from a commit that fixes a bug, traces the history backward, and estimates the commit that likely introduced the bug. SZZBench provides a basis for checking, with small controlled Git repositories, what kinds of histories make this estimation work well and what kinds of histories make it fail.

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

For Graph scenarios, use the following commands:

```bash
szzbench validate-graph
szzbench generate-graph
szzbench verify-graph
szzbench new-graph-scenario
```

`scenario.graph.yml` is more expressive than the normal `scenario.yml`, but it is still positioned as an evolving draft schema.

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

## Directory structure

The current main directory structure is as follows.

```text
SZZBench/
├── pyproject.toml
├── README.md
├── .gitignore
│
├── src/
│   └── szzbench/
│       ├── cli.py
│       ├── scenario.py
│       ├── validator.py
│       ├── generator.py
│       ├── verifier.py
│       ├── evaluator.py
│       ├── operations.py
│       ├── gitutils.py
│       ├── cleaner.py
│       ├── scenario_builder.py
│       │
│       ├── graph_scenario.py
│       ├── graph_validator.py
│       ├── graph_generator.py
│       ├── graph_verifier.py
│       ├── graph_operations.py
│       ├── graph_simulator.py
│       └── graph_scenario_builder.py
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
├── examples/
│   └── basic/
│       └── simple-line-modification/
│
├── tools/
│   ├── adapters/
│   ├── scenario-editor/
│   └── generated-repo-viewer/
│
└── tests/
```

The main roles are as follows.

| Path | Role |
|---|---|
| `src/szzbench/` | Main Python implementation. Contains the CLI, validator, generator, verifier, evaluator, and related modules. |
| `scenarios/` | Location for normal `SZZ-XXXX` scenarios. |
| `advanced-scenarios/` | Location for Graph `SZZG-XXXX` scenarios. |
| `generated-input-repos/` | Output location for Git repositories generated by the generator. This is not tracked by Git. |
| `tools/adapters/` | Example adapters that convert SZZ tool-specific outputs into SZZBench predictions. |
| `tools/scenario-editor/` | Local Web application for creating normal scenarios. |
| `tools/generated-repo-viewer/` | Local Web application for inspecting generated Git repositories. |
| `tests/` | Test code. |

## Installation

Python 3.10 or later is required.

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

### generate

Generate an actual Git repository from `scenario.yml`.

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force
```

Add `--no-verify` to skip verification after generation.

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force   --no-verify
```

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

Verify that a generated repository corresponds to `scenario.yml`.

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml
```

You can also explicitly specify `commit-map.json` if necessary.

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml   --commit-map generated-input-repos/SZZ-0006/default/metadata/commit-map.json
```

### new-scenario

Create a skeleton for a new normal scenario.

```bash
szzbench new-scenario   --title "Formatting after bug introduction"   --category formatting   --factor formatting   --factor intermediate-history
```

By default, a directory like the following is created, and `scenarios/index.yml` is also updated.

```text
scenarios/SZZ-XXXX/
├── scenario.yml
└── README.md
```

## Using Graph scenarios

### validate-graph

Validate the structure and references in `scenario.graph.yml`.

```bash
szzbench validate-graph advanced-scenarios/SZZG-0001/scenario.graph.yml
```

Use `--simulate` to simulate Graph operations in memory.

```bash
szzbench validate-graph   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

Use `--strict-paths` for stricter checks of path / entity shapes.

```bash
szzbench validate-graph   --strict-paths   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

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

`graph-map.json` records additional information for Graph scenarios. It includes information such as branches, parents, and roles.

### verify-graph

Verify that a generated repository corresponds to `scenario.graph.yml`.

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml
```

You can also explicitly specify `commit-map.json` and `graph-map.json` if necessary.

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml   --commit-map generated-input-repos/SZZG-0001/default/metadata/commit-map.json   --graph-map generated-input-repos/SZZG-0001/default/metadata/graph-map.json
```

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

`fix_commit` is optional for evaluation. `inducing_commit` may be an actual Git hash, a unique hash prefix, or a logical commit id from `commit-map.json`.

Use `--include-generated` when the predictions file only contains scenarios where a tool produced at least one BIC. SZZBench then evaluates every generated repository under `--generated-root` and treats missing prediction records as empty predictions.

For Graph scenarios, `--evaluation-variant` selects a named `expected_szz.evaluation_variants` entry such as `direct-only`, `origin-aware`, or `relaxed-with-credit`. If it is omitted, SZZBench uses the scenario's `default_variant` when one is defined, otherwise it uses `expected_szz.commit_level`. Hyphen and underscore differences are normalized for matching. This option is independent of `--variant`, which selects the generated repository directory under each scenario.

The JSON report keeps the strict fields (`true_positives`, `false_positives`, `false_negatives`) and also includes Graph-specific details when available: `evaluation_policy`, `evaluation_variant`, `hard_false_positives`, `related_origin_hits`, `related_but_not_correct_hits`, `acceptable_related_hits`, `weighted_credit`, `minimum_required_met`, and `top_k`.

For SZZ Unleashed output, convert the generated `fix_and_introducers_pairs.json` files first:

```bash
tools/adapters/szz_unleashed_to_predictions.py \
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

### new-graph-scenario

Create a skeleton for a new Graph scenario.

```bash
szzbench new-graph-scenario   --title "BIC on feature branch and BFC on main"   --category branch-merge   --factor branch   --factor merge
```

By default, a directory like the following is created, and `advanced-scenarios/index.yml` is also updated.

```text
advanced-scenarios/SZZG-XXXX/
├── scenario.graph.yml
└── README.md
```

## generate-all-repos

Generate repositories for all normal scenarios under `scenarios/` and all Graph scenarios under `advanced-scenarios/` with one command.

```bash
szzbench generate-all-repos
```

The command scans the following files.

- `scenarios/*/scenario.yml`
- `advanced-scenarios/*/scenario.graph.yml`

Each generated repository is written under `generated-input-repos/<SCENARIO_ID>/default/`.

By default, if that output directory already contains `repo/.git`, the scenario is skipped. This makes the command safe to run repeatedly when you only want to generate missing repositories.

To remove existing generated repositories and create them again, use `--overwrite`.

```bash
szzbench generate-all-repos --overwrite
```

`--overwrite` deletes the existing `generated-input-repos/<SCENARIO_ID>/default/` output for each scenario before generating it again.

Add `--no-verify` to skip post-generation verification for all generated repositories.

```bash
szzbench generate-all-repos --no-verify
```

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

## Auxiliary tools

### Scenario editor

`tools/scenario-editor/` is a local Web application for creating normal `scenario.yml` scenarios.

```bash
cd tools/scenario-editor
npm install
npm run dev
```

Open the following URL in a browser.

```text
http://127.0.0.1:5173
```

This editor can create `scenario.yml` and `README.md` by entering metadata, source-code versions, and BIC / BFC information. Through a local Node.js API, it can also save files directly under `scenarios/SZZ-XXXX/`.

At present, it is mainly intended for normal scenarios. It does not support editing Graph scenarios.

### Generated repository viewer

`tools/generated-repo-viewer/` is a local Web application for inspecting generated Git repositories.

```bash
cd tools/generated-repo-viewer
npm install
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

Dependencies for JavaScript/TypeScript tools are installed under `node_modules/`, but this directory should not be tracked by Git. If needed, recreate it by running `npm install` or `npm ci` in each tool directory.

Python virtual environments such as `.venv/` should also not be tracked by Git. Recreate them in each local environment when needed.

## Creating a distribution ZIP

To create a ZIP file that contains only files tracked by Git, use the following command.

```bash
git archive --format=zip --prefix=SZZBench/ --output=SZZBench_source.zip HEAD
```

This creates a ZIP file that excludes files not tracked by Git, such as `node_modules/`, `.venv/`, and `generated-input-repos/`.

## Current notes

- `scenario.graph.yml` is more expressive than the normal `scenario.yml`, but it is still an evolving draft schema.
- For Graph scenarios, both `validate-graph --simulate` and `verify-graph` are recommended because the history structures and oracles are complex.
- Generated repositories are derived artifacts, so they should generally not be tracked by Git.
- SZZBench is not intended to replace large real-project-based oracles. It is a complementary benchmark for checking SZZ failure modes with small, controlled histories.

---

# 日本語版

# SZZBench

SZZBench は、SZZ 手法を評価するための人工 Git リポジトリ生成・検証ツールです。

SZZ では、バグを修正したコミットから過去の履歴をたどり、そのバグを混入した可能性が高いコミットを推定します。SZZBench は、この推定がどのような履歴ではうまく動き、どのような履歴では失敗しやすいのかを、制御された小さな Git リポジトリで確認するための基盤です。

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

Graph シナリオでは、次のコマンドを使います。

```bash
szzbench validate-graph
szzbench generate-graph
szzbench verify-graph
szzbench new-graph-scenario
```

`scenario.graph.yml` は、通常の `scenario.yml` より表現力が高い一方で、まだ draft schema として発展中の位置付けです。

## ディレクトリ構成

現在の主なディレクトリ構成は以下です。

```text
SZZBench/
├── pyproject.toml
├── README.md
├── .gitignore
│
├── src/
│   └── szzbench/
│       ├── cli.py
│       ├── scenario.py
│       ├── validator.py
│       ├── generator.py
│       ├── verifier.py
│       ├── evaluator.py
│       ├── operations.py
│       ├── gitutils.py
│       ├── cleaner.py
│       ├── scenario_builder.py
│       │
│       ├── graph_scenario.py
│       ├── graph_validator.py
│       ├── graph_generator.py
│       ├── graph_verifier.py
│       ├── graph_operations.py
│       ├── graph_simulator.py
│       └── graph_scenario_builder.py
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
├── examples/
│   └── basic/
│       └── simple-line-modification/
│
├── tools/
│   ├── adapters/
│   ├── scenario-editor/
│   └── generated-repo-viewer/
│
└── tests/
```

主な役割は以下です。

| パス | 役割 |
|---|---|
| `src/szzbench/` | Python 実装本体。CLI、validator、generator、verifier、evaluator など。 |
| `scenarios/` | 通常シナリオ `SZZ-XXXX` を管理する場所。 |
| `advanced-scenarios/` | Graph シナリオ `SZZG-XXXX` を管理する場所。 |
| `generated-input-repos/` | generator が生成する Git リポジトリの出力先。Git 管理対象外。 |
| `tools/adapters/` | SZZ ツール固有の出力を SZZBench predictions 形式へ変換するサンプル adapter。 |
| `tools/scenario-editor/` | 通常シナリオを作成するためのローカル Web アプリ。 |
| `tools/generated-repo-viewer/` | 生成済み Git リポジトリを確認するためのローカル Web アプリ。 |
| `tests/` | テストコード。 |

## インストール

Python 3.10 以上が必要です。

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

### generate

`scenario.yml` から実際の Git リポジトリを生成します。

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force
```

`--no-verify` を付けると、生成後の verify をスキップします。

```bash
szzbench generate   scenarios/SZZ-0006/scenario.yml   --out generated-input-repos/SZZ-0006/default   --force   --no-verify
```

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

生成済みリポジトリが `scenario.yml` と対応しているかを検査します。

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml
```

必要に応じて `commit-map.json` を明示できます。

```bash
szzbench verify   generated-input-repos/SZZ-0006/default/repo   --scenario scenarios/SZZ-0006/scenario.yml   --commit-map generated-input-repos/SZZ-0006/default/metadata/commit-map.json
```

### new-scenario

新しい通常シナリオの雛形を作成します。

```bash
szzbench new-scenario   --title "Formatting after bug introduction"   --category formatting   --factor formatting   --factor intermediate-history
```

デフォルトでは、次のようなディレクトリが作成され、`scenarios/index.yml` も更新されます。

```text
scenarios/SZZ-XXXX/
├── scenario.yml
└── README.md
```

## Graph シナリオの使い方

### validate-graph

`scenario.graph.yml` の構造や参照関係を検査します。

```bash
szzbench validate-graph advanced-scenarios/SZZG-0001/scenario.graph.yml
```

Graph operation をメモリ上でシミュレーションして確認したい場合は、`--simulate` を使います。

```bash
szzbench validate-graph   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

より厳密な path / entity 形状の検査を行う場合は、`--strict-paths` を使います。

```bash
szzbench validate-graph   --strict-paths   --simulate   advanced-scenarios/SZZG-0001/scenario.graph.yml
```

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

`graph-map.json` は、Graph シナリオ向けの追加情報を記録します。branch、parent、role などの情報を含みます。

### verify-graph

生成済みリポジトリが `scenario.graph.yml` と対応しているかを検査します。

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml
```

必要に応じて `commit-map.json` と `graph-map.json` を明示できます。

```bash
szzbench verify-graph   generated-input-repos/SZZG-0001/default/repo   --scenario advanced-scenarios/SZZG-0001/scenario.graph.yml   --commit-map generated-input-repos/SZZG-0001/default/metadata/commit-map.json   --graph-map generated-input-repos/SZZG-0001/default/metadata/graph-map.json
```

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

評価に必須なのは `scenario_id` と `inducing_commit` です。`fix_commit` は任意です。`inducing_commit` には実 Git hash、ユニークな hash prefix、または `commit-map.json` の論理 commit id を指定できます。

予測ファイルに「BIC が 1 件以上出たシナリオ」だけが含まれる場合は、`--include-generated` を使います。この場合、SZZBench は `--generated-root` 以下の生成済みリポジトリをすべて評価対象にし、prediction record がないシナリオを空予測として扱います。

Graph scenario では、`--evaluation-variant` で `expected_szz.evaluation_variants` に定義された `direct-only`、`origin-aware`、`relaxed-with-credit` などの評価 variant を選べます。省略した場合は、シナリオに `default_variant` があればそれを使い、なければ `expected_szz.commit_level` を使います。variant 名の照合ではハイフンとアンダースコアの違いを吸収します。このオプションは、生成リポジトリのディレクトリを選ぶ `--variant` とは別物です。

JSON レポートには従来の `true_positives`、`false_positives`、`false_negatives` に加えて、Graph scenario 用の `evaluation_policy`、`evaluation_variant`、`hard_false_positives`、`related_origin_hits`、`related_but_not_correct_hits`、`acceptable_related_hits`、`weighted_credit`、`minimum_required_met`、`top_k` も出力されます。

SZZ Unleashed の出力は、先に `fix_and_introducers_pairs.json` を共通 prediction 形式へ変換します。

```bash
tools/adapters/szz_unleashed_to_predictions.py \
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

### new-graph-scenario

新しい Graph シナリオの雛形を作成します。

```bash
szzbench new-graph-scenario   --title "BIC on feature branch and BFC on main"   --category branch-merge   --factor branch   --factor merge
```

デフォルトでは、次のようなディレクトリが作成され、`advanced-scenarios/index.yml` も更新されます。

```text
advanced-scenarios/SZZG-XXXX/
├── scenario.graph.yml
└── README.md
```

## generate-all-repos

`scenarios/` 以下の通常シナリオと、`advanced-scenarios/` 以下の Graph シナリオから、まとめてリポジトリを生成します。

```bash
szzbench generate-all-repos
```

このコマンドは、次のファイルを走査します。

- `scenarios/*/scenario.yml`
- `advanced-scenarios/*/scenario.graph.yml`

各リポジトリは `generated-input-repos/<SCENARIO_ID>/default/` 以下に生成されます。

デフォルトでは、出力先に `repo/.git` が存在する場合、そのシナリオはスキップされます。そのため、不足しているリポジトリだけを生成したい場合にも繰り返し実行できます。

既存の生成済みリポジトリを削除して作り直す場合は、`--overwrite` を使います。

```bash
szzbench generate-all-repos --overwrite
```

`--overwrite` は、対象シナリオの既存出力 `generated-input-repos/<SCENARIO_ID>/default/` を削除してから再生成します。

生成後の検証をまとめてスキップする場合は、`--no-verify` を使います。

```bash
szzbench generate-all-repos --no-verify
```

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

## 補助ツール

### Scenario editor

`tools/scenario-editor/` は、通常シナリオ `scenario.yml` を作成するためのローカル Web アプリです。

```bash
cd tools/scenario-editor
npm install
npm run dev
```

ブラウザで次を開きます。

```text
http://127.0.0.1:5173
```

この editor は、メタデータ、ソースコードの各バージョン、BIC / BFC 情報を入力し、`scenario.yml` と `README.md` を作成できます。ローカル Node.js API を通じて、`scenarios/SZZ-XXXX/` 以下へ直接保存することもできます。

現状では、主に通常シナリオ向けです。Graph シナリオの編集には対応していません。

### Generated repository viewer

`tools/generated-repo-viewer/` は、生成済み Git リポジトリを確認するためのローカル Web アプリです。

```bash
cd tools/generated-repo-viewer
npm install
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

JavaScript/TypeScript ツールの依存ライブラリは `node_modules/` に入りますが、これは Git 管理しません。必要な場合は、各 tool ディレクトリで `npm install` または `npm ci` を実行して再作成します。

Python の仮想環境 `.venv/` も Git 管理しません。必要な場合は、各環境で作り直します。

## 配布用 ZIP の作成

Git 管理下のファイルだけを ZIP にしたい場合は、次を使います。

```bash
git archive --format=zip --prefix=SZZBench/ --output=SZZBench_source.zip HEAD
```

これにより、`node_modules/`、`.venv/`、`generated-input-repos/` などの Git 管理外ファイルを含まない ZIP を作成できます。

## 現在の注意点

- `scenario.graph.yml` は通常の `scenario.yml` より表現力が高いですが、まだ発展中の draft schema です。
- Graph シナリオでは、履歴構造や oracle が複雑なため、`validate-graph --simulate` と `verify-graph` の両方で確認することを推奨します。
- 生成されたリポジトリは派生物なので、基本的には Git 管理しません。
- SZZBench は、実プロジェクト由来の大規模 oracle を置き換えるものではありません。SZZ の failure mode を小さく制御された履歴で確認するための補助的なベンチマークです。
