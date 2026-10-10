# Tests

Run `pytest` from the repository root. `tests/conftest.py` puts this checkout's `src` first on `sys.path` and on `PYTHONPATH`, so the suite exercises the code next to it, and so do the tests that start `python -m szzbench.cli` in a subprocess. No `pip install -e .` is needed for that.

## What the suite needs

- **A JDK** (`javac` and `java`). The tests marked `needs_jdk` compile and run the scenarios' Java code to check what their READMEs claim.
- **Node.js 22.18 or later, and `npm ci` in `tools/scenario-editor`.** `test_scenario_editor.py` needs both.
- **`npm ci` in `tools/generated-repo-viewer`.** `test_repo_viewer.py` starts the viewer's server on a scratch copy of the layout.

Without these tools, the tests that need them are skipped. `pytest -rs` lists every skip with its reason.

## CI

`.github/workflows/tests.yml` runs on every push to `main`, and a later push does not cancel the run of an earlier one; on a pull request, a new commit cancels the run of the commit before it (issue #205). Pull request CI and its required status checks are temporarily paused. It does two things:

- **Runs the whole suite** on Linux, using `pytest -rs`, in two jobs:
  - Python 3.14 with the current Git of the `ubuntu-latest` runner;
  - Python 3.10, the oldest version `pyproject.toml` declares, in a `python:3.10-bookworm` container with Debian 12's Git 2.39. Git before 2.45 has no `--ref-format`, so `init_args()` leaves it out, and this job takes that path.

  Both jobs provide the tools above: JDK 21, and Node.js 22 with `npm ci` in `tools/scenario-editor` and `tools/generated-repo-viewer`. No test should skip there for a missing tool; the log lists the skips that remain. One of them is `test_quickstart_numbers.py::test_rescoring_the_example_reproduces_the_report`, which re-scores the recorded PyDriller run and needs current outputs under `generated-input-repos/`, which CI does not generate (issue #189).
- **Builds the two web tools** under `tools/`.

To resume pull request CI, uncomment `pull_request:` in `.github/workflows/tests.yml` and restore these required status checks for `main` (with GitHub Actions as their source):

- `pytest (Python 3.14, the runner's Git)`
- `pytest (Python 3.10, Git 2.39 of Debian 12)`
- `build scenario-editor`
- `build generated-repo-viewer`

Windows is not tested ([#109](https://github.com/higolab/SZZBench/issues/109)).

## Conventions

These conventions come from the audit in issue #107.

- **Shared helpers live in `tests/support.py`.** Use them instead of copying them:
  - Git: `git`, `git_stdout`, `git_bytes` and `export_tree`;
  - generating shipped scenarios: `GeneratedScenarios`;
  - blame attribution: `blame_owners` and `logical_id`;
  - the Java driver: `run_driver`;
  - the `needs_jdk` marker.
- **Run Git through those helpers.** They run it in SZZBench's isolated environment (issue #96), so a developer's Git configuration cannot change what a test sees.
  - This holds for `test_git_isolation.py` too. It runs SZZBench under hostile Git environments, but sets up and reads its own repositories through the helpers.
  - `test_suite_conventions.py` fails on any direct `git` call that does not pass `env=git_env()`.
- **Parametrize a check about one scenario over that scenario only.** Do not parametrize it over the whole family and skip the others. A family-wide check takes the family through a parametrized fixture backed by one `GeneratedScenarios`, so each scenario is generated once per module.
- **Parametrize suite-wide checks by scenario id.** This applies to README headers, template boilerplate and Java names. A failure then names the scenario, and `-k SZZ-0006` selects it. Each case takes well under half a second.
