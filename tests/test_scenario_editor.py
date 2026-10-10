"""The Scenario Editor writes what SZZBench's own checks accept (issue #97).

The editor predates ``meta.tier``, the role-neutral message policy and the
generated README header, and nothing compared its output with the Python side:
its default scenario drew W460 (no tier) and W410 (``Introduce bug``) from
``validate --lint``, the README it saved drew W455 twice, and saving re-dumped
``scenarios/index.yml``, changing 3,764 of its 1,881 lines.  These tests run
the editor's own TypeScript (``src/scenarioModel.ts``) with Node and check what
it generates with the Python validator, and drive the save and download
endpoints (``server/index.js``) against a scratch copy of the repository
layout.  The review of PR #101 found the download path still handing out a
README without its generated header, so the files it returns are checked where
the documentation says to put them, with no ``readme --write`` step.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import yaml

from szzbench.generator import generate_repository

ROOT = Path(__file__).resolve().parents[1]

EDITOR = ROOT / "tools/scenario-editor"
MODEL = EDITOR / "src/scenarioModel.ts"

DRIVER = """
import * as model from %(model)s;
const overrides = JSON.parse(process.argv[2] || '{}');
// fault types picked from the page's menu in turn, after the overrides (issue #192)
const picks = JSON.parse(process.argv[3] || '[]');
const state = picks.reduce((s, type) => model.selectFaultType(s, type), { ...model.initialState(), ...overrides });
process.stdout.write(JSON.stringify({
  yaml: model.generateScenarioYaml(state),
  readme: model.generateReadme(state),
  next: model.nextVersion(state),
  checks: model.localValidate({ ...state, versions: [...state.versions, model.nextVersion(state)] }),
}));
"""


def _node_runs_typescript() -> bool:
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(["node", "--input-type=module", "-e", f"import {json.dumps(MODEL.as_uri())};"],
                           capture_output=True, text=True)
    return probe.returncode == 0


pytestmark = pytest.mark.skipif(not _node_runs_typescript(), reason="needs a Node.js that runs TypeScript (22.18+)")


def _model(tmp_path: Path, picks: tuple[str, ...] = (), **overrides) -> dict:
    driver = tmp_path / "driver.mjs"
    driver.write_text(DRIVER % {"model": json.dumps(MODEL.as_uri())}, encoding="utf-8")
    completed = subprocess.run(["node", str(driver), json.dumps(overrides), json.dumps(list(picks))],
                               capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def _cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], capture_output=True, text=True, cwd=cwd,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "src")})


def _save_as_the_server_does(tmp_path: Path, generated: dict) -> Path:
    """scenario.yml and README.md in a scenarios/ layout, with the header `readme --write` inserts."""
    scenarios = tmp_path / "scenarios"
    (tmp_path / "advanced-scenarios").mkdir()
    directory = scenarios / "SZZ-0002"
    directory.mkdir(parents=True)
    (directory / "scenario.yml").write_text(generated["yaml"], encoding="utf-8")
    (directory / "README.md").write_text(generated["readme"], encoding="utf-8")
    written = _cli("readme", "--write", "--scenarios-root", str(scenarios),
                   "--advanced-scenarios-root", str(tmp_path / "advanced-scenarios"), str(directory))
    assert written.returncode == 0, written.stdout + written.stderr
    return directory / "scenario.yml"


def _lint(path: Path) -> dict:
    return json.loads(_cli("validate", "--lint", "--json", str(path)).stdout)


def test_the_default_scenario_with_a_tier_passes_strict_lint_with_no_finding(tmp_path):
    path = _save_as_the_server_does(tmp_path, _model(tmp_path, tier="control"))
    report = _lint(path)
    assert report["findings"] == [], report
    assert _cli("validate", "--lint", "--strict", str(path)).returncode == 0


def test_the_default_scenario_generates_and_verifies(tmp_path):
    path = _save_as_the_server_does(tmp_path, _model(tmp_path, tier="control"))
    commit_map, verify = generate_repository(path, tmp_path / "out", force=True)
    assert sorted(commit_map) == ["c0", "c1", "c2"] and not verify.has_errors(), verify.to_dict()


def test_without_a_tier_lint_asks_for_one(tmp_path):
    report = _lint(_save_as_the_server_does(tmp_path, _model(tmp_path)))
    assert [finding["code"] for finding in report["findings"]] == ["W460"]


def test_the_defaults_disclose_no_role_and_no_answer(tmp_path):
    generated = _model(tmp_path, tier="control")
    messages = [line.split(":", 1)[1].strip().strip('"') for line in generated["yaml"].splitlines()
                if line.startswith("    message:")]
    assert messages == ["Add the range check", "Exclude the bounds from the range check",
                        "Include the bounds in the range check"]
    authors = {line.split(":", 1)[1].strip() for line in generated["yaml"].splitlines()
               if line.startswith("    author:")}
    assert len(authors) == 1        # one author for every commit, so no author names the BIC
    assert "    date:" not in generated["yaml"]      # left to generation's deterministic dates


def test_an_added_version_starts_without_a_message_and_the_checks_ask_for_one(tmp_path):
    generated = _model(tmp_path, tier="control")
    assert generated["next"]["id"] == "c3" and generated["next"]["message"] == ""
    assert "WARN: write a message describing the change for c3" in generated["checks"]


def test_the_category_is_a_code_from_the_vocabulary(tmp_path):
    generated = _model(tmp_path, tier="control", categoryCode="S3")
    assert '  category: "Intermediate noise and history noise"' in generated["yaml"]
    assert '  category_code: "S3"' in generated["yaml"]


@pytest.mark.parametrize("typed, errors", [("main", []), ("release/2024.1", []), ("a b", ["E015"]), ("-x", ["E015"]),
                                           ("", ["E015"]), ("Main.lock", ["E015"])])
def test_the_default_branch_field_is_checked_as_validate_checks_a_branch_name(tmp_path, typed, errors):
    """The free-text "Default branch" field is written as typed.  A name Git refuses, or an empty field, used
    to be saved and fail ``generate`` with Git's message; validate refuses it now (E015, issue #239), so the
    server does not save it."""
    generated = _model(tmp_path, tier="control", defaultBranch=typed)
    assert yaml.safe_load(generated["yaml"])["repository"]["default_branch"] == typed
    report = _lint(_save_as_the_server_does(tmp_path, generated))
    assert [(f["code"], f["location"]) for f in report["findings"] if f["severity"] == "ERROR"] == \
        [(code, "repository.default_branch") for code in errors]


# ---------------------------------------------------------------------------
# multi-line statements and the omission example (issue #192)
# ---------------------------------------------------------------------------

HEAD = "package example;\n\npublic class Range {\n    public boolean contains(int value, int min, int max) {\n"
TAIL = "        return value >= min && value <= max;\n    }\n}\n"
GUARD = "        if (value < 0) {\n            return false;\n        }\n"
ENDINGS = pytest.mark.parametrize("ending", ["\n", ""], ids=["final-newline", "no-final-newline"])


def _version(index: int, role: str, message: str, source: str) -> dict:
    return {"id": f"c{index}", "role": role, "message": message, "author": "Alice <alice@example.com>", "date": "",
            "source": source}


def test_a_blank_author_field_writes_no_author(tmp_path):
    """validate refuses `author: ""` (E014, issue #152): a blank author field leaves the author to the generator,
    as a blank date field leaves the date."""
    def source(op: str) -> str:
        return HEAD + f"        return value {op} min && value {op.replace('>', '<')} max;\n    }}\n}}\n"

    versions = [dict(_version(0, "initial", "Add the range check", source(">=")), author=""),
                dict(_version(1, "bug_introducing", "Exclude the bounds from the range check", source(">")), author="  "),
                _version(2, "bug_fixing", "Include the bounds in the range check", source(">="))]
    generated = _model(tmp_path, tier="control", versions=versions)
    commits = yaml.safe_load(generated["yaml"])["commits"]
    assert [commit.get("author") for commit in commits] == [None, None, "Alice <alice@example.com>"]
    path = _save_as_the_server_does(tmp_path, generated)
    assert _cli("validate", "--lint", "--strict", str(path)).returncode == 0, _lint(path)


def _strict_and_generate(tmp_path: Path, path: Path) -> None:
    completed = _cli("validate", "--lint", "--strict", str(path))
    assert completed.returncode == 0, completed.stdout
    commit_map, verify = generate_repository(path, tmp_path / "out", force=True)
    assert sorted(commit_map) == ["c0", "c1", "c2"] and not verify.has_errors(), verify.to_dict()


@ENDINGS
def test_a_multi_line_omission_statement_keeps_its_indentation(tmp_path, ending):
    """The issue's reproduction.  The statement as the source indents it used to
    go under ``|`` with eight spaces more, YAML stripped the method's indentation
    on load, and E311 refused the save.  With or without a final newline, it is
    stored as typed and found in the file."""
    statement = GUARD.rstrip("\n") + ending
    generated = _model(tmp_path, tier="control", faultType="omission", categoryCode="S2",
                       factors=["single-bic", "single-bfc", "omission-bug"],
                       missingStatement=statement, addedStatement=statement,
                       versions=[_version(0, "initial", "Add the range check with the guard", HEAD + GUARD + TAIL),
                                 _version(1, "bug_introducing", "Drop the negative guard", HEAD + TAIL),
                                 _version(2, "bug_fixing", "Restore the negative guard", HEAD + GUARD + TAIL)])
    path = _save_as_the_server_does(tmp_path, generated)
    bug = yaml.safe_load(path.read_text(encoding="utf-8"))["bugs"][0]
    assert bug["fault"]["missing_statement"] == statement and bug["fix"]["added_statement"] == statement
    assert "OK: added statement appears in BFC version" in generated["checks"]
    _strict_and_generate(tmp_path, path)


@ENDINGS
def test_a_multi_line_line_modification_statement_is_not_folded(tmp_path, ending):
    """A double-quoted scalar over two lines folded the break to a space on load,
    so neither statement was in the file (E301, E311).  The fault keeps the
    first line's indentation, the fix starts at ``return`` as SZZ-0081's does."""
    def wrapped(low: str, high: str) -> str:
        return HEAD + f"        return value {low} min\n                && value {high} max;\n    }}\n}}\n"

    fault = "        return value > min\n                && value < max;" + ending
    fix = "return value >= min\n                && value <= max;" + ending
    versions = [_version(0, "initial", "Add the range check", wrapped(">=", "<=")),
                _version(1, "bug_introducing", "Exclude the bounds from the range check", wrapped(">", "<")),
                _version(2, "bug_fixing", "Include the bounds in the range check", wrapped(">=", "<="))]
    generated = _model(tmp_path, tier="control", faultStatement=fault, fixStatement=fix, versions=versions)
    path = _save_as_the_server_does(tmp_path, generated)
    bug = yaml.safe_load(path.read_text(encoding="utf-8"))["bugs"][0]
    assert (bug["fault"]["statement"], bug["fix"]["statement"]) == (fault, fix)
    assert bug["expected_szz"]["line_level"]["faulty_statements"] == [fault]
    assert {"OK: fault statement appears in BIC version",
            "OK: fix statement appears in BFC version"} <= set(generated["checks"])
    _strict_and_generate(tmp_path, path)


def test_picking_omission_starts_from_an_example_that_passes_strict_lint(tmp_path):
    """The omission defaults named ``s == null``, which the Range source never
    had, and the line-modification history cannot carry an omission oracle in
    any case: its fix modifies a line, and an omission fix only adds (W420)."""
    generated = _model(tmp_path, picks=("omission",), tier="control")
    # as SZZ-0047 writes them: the missing statement on its own, the added one as the method indents it
    assert '      missing_statement: |2\n        if (min > max) {' in generated["yaml"]
    assert '      added_statement: |2\n                if (min > max) {' in generated["yaml"]
    assert [check for check in generated["checks"] if check.startswith("WARN")] == [
        "WARN: write a message describing the change for c3"]                           # the appended version only
    _strict_and_generate(tmp_path, _save_as_the_server_does(tmp_path, generated))


def test_picking_a_fault_type_swaps_only_the_example_fields_left_alone(tmp_path):
    there_and_back = _model(tmp_path, picks=("omission", "line_modification"), tier="control")
    assert there_and_back["yaml"] == _model(tmp_path, tier="control")["yaml"]
    edited = _model(tmp_path, picks=("omission",), tier="control", bugTitle="Reversed bounds slip through")
    assert '    title: "Reversed bounds slip through"' in edited["yaml"]                     # the author's, kept
    assert '    message: "Add the range class"' in edited["yaml"]                            # the example's, swapped


def test_the_checks_warn_where_validate_refuses_the_statement(tmp_path):
    """The guard as SZZ-0047 writes a missing statement, on its own, is not in
    the BFC's file: the page says so before the save is refused with E311."""
    on_its_own = 'if (min > max) {\n    throw new IllegalArgumentException("min must not exceed max");\n}\n'
    generated = _model(tmp_path, picks=("omission",), tier="control", addedStatement=on_its_own)
    assert ("WARN: added statement does not appear in BFC version (it is matched exactly, indentation included)"
            in generated["checks"])
    assert [finding["code"] for finding in _lint(_save_as_the_server_does(tmp_path, generated))["findings"]] == ["E311"]


@pytest.mark.parametrize("typed", ["", "  \n"], ids=["empty", "blank"])
def test_a_blank_missing_statement_writes_no_key_and_the_checks_say_validate_refuses_it(tmp_path, typed):
    """The editor wrote `missing_statement: ""`, which E351 accepted until issue #237.  A blank
    field writes no key, as a blank author field does, and the save is refused with E351."""
    generated = _model(tmp_path, picks=("omission",), tier="control", missingStatement=typed)
    assert "missing_statement" not in yaml.safe_load(generated["yaml"])["bugs"][0]["fault"]
    assert "WARN: missing statement is empty (validate refuses an omission without one, E351)" in generated["checks"]
    report = _lint(_save_as_the_server_does(tmp_path, generated))
    assert [(f["code"], f["location"]) for f in report["findings"] if f["severity"] == "ERROR"] == \
        [("E351", "bugs[0].fault.missing_statement")]


@pytest.mark.parametrize("tail", ["", "}\n"], ids=["method", "method-and-closing-brace"])
def test_a_source_with_an_indented_first_line_loads_back_as_typed(tmp_path, tail):
    """A plain ``|`` block takes its indentation from its first line that is not
    empty, so a source pasted from an indented line set it too deep: a method on
    its own lost its indentation on load, and with the class's closing brace
    after it the scenario did not load at all."""
    def method(low: str, high: str) -> str:
        return ("    public boolean contains(int value, int min, int max) {\n"
                f"        return value {low} min && value {high} max;\n    }}\n{tail}")

    sources = [method(">=", "<="), method(">", "<"), method(">=", "<=")]
    versions = [_version(0, "initial", "Add the range check", sources[0]),
                _version(1, "bug_introducing", "Exclude the bounds from the range check", sources[1]),
                _version(2, "bug_fixing", "Include the bounds in the range check", sources[2])]
    path = _save_as_the_server_does(tmp_path, _model(tmp_path, tier="control", versions=versions))
    commits = yaml.safe_load(path.read_text(encoding="utf-8"))["commits"]
    assert [commits[0]["operations"][0]["content"]] + [c["operations"][0]["new"] for c in commits[1:]] == sources
    assert [c["operations"][0]["old"] for c in commits[1:]] == sources[:2]
    _strict_and_generate(tmp_path, path)


# ---------------------------------------------------------------------------
# the save endpoint
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    if not (EDITOR / "node_modules/express").is_dir():
        pytest.skip("needs the editor's dependencies (npm ci in tools/scenario-editor)")
    root = tmp_path / "repo"
    (root / "scenarios").mkdir(parents=True)
    shutil.copy(ROOT / "scenarios/index.yml", root / "scenarios/index.yml")
    (root / "docs").mkdir()
    shutil.copy(ROOT / "docs/retired-ids.md", root / "docs/retired-ids.md")
    (root / "src").symlink_to(ROOT / "src")
    port = _free_port()
    process = subprocess.Popen(["node", str(EDITOR / "server/index.js")], cwd=EDITOR,
                               env={**os.environ, "PORT": str(port), "SZZBENCH_REPO_ROOT": str(root),
                                    "SZZBENCH_PYTHON": sys.executable},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    else:
        process.kill()
        pytest.fail("the editor server did not start")
    yield base, root
    process.kill()
    process.wait()


def _post(base: str, body: dict, endpoint: str = "save") -> tuple[int, dict]:
    request = urllib.request.Request(f"{base}/api/scenarios/{endpoint}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_saving_validates_writes_the_header_and_inserts_one_index_entry(server, tmp_path):
    base, root = server
    generated = _model(tmp_path, tier="control")
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": generated["yaml"], "readme": generated["readme"]})
    assert status == 200, data
    assert data["findings"] == []
    readme = (root / "scenarios/SZZ-0002/README.md").read_text(encoding="utf-8")
    assert "<!-- szzbench:header" in readme and "## Factors" not in readme
    assert _lint(root / "scenarios/SZZ-0002/scenario.yml")["findings"] == []

    before = (ROOT / "scenarios/index.yml").read_text(encoding="utf-8").splitlines()
    after = (root / "scenarios/index.yml").read_text(encoding="utf-8").splitlines()
    start = after.index("- id: SZZ-0002")
    added = after[start:start + 10]
    assert added == ["- id: SZZ-0002", "  title: New SZZ scenario", "  slug: new-szz-scenario", "  category_code: S1",
                     "  category: Basic semantic line changes", "  factors:", "  - single-bic", "  - single-bfc",
                     "  - line-modification", "  difficulty: medium"]
    assert after[:start] + after[start + 12:] == before      # every other line, byte for byte
    assert after[start + 12] == "- id: SZZ-0005"             # inserted in id order


def test_saving_the_omission_example_writes_it(server, tmp_path):
    """Picking omission left statements that no version contained, and the save
    endpoint answered 400 (issue #192)."""
    base, root = server
    generated = _model(tmp_path, picks=("omission",), tier="control")
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": generated["yaml"], "readme": generated["readme"]})
    assert status == 200 and data["findings"] == [], data
    assert (root / "scenarios/SZZ-0002/scenario.yml").read_text(encoding="utf-8") == generated["yaml"]


def test_saving_without_a_tier_is_refused(server, tmp_path):
    base, root = server
    generated = _model(tmp_path)
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": generated["yaml"], "readme": generated["readme"]})
    assert status == 400 and "meta.tier" in data["error"]
    assert not (root / "scenarios/SZZ-0002").exists()


def test_a_scenario_with_a_validation_error_is_not_saved(server, tmp_path):
    base, root = server
    generated = _model(tmp_path, tier="control", bfc="c9")
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": generated["yaml"], "readme": generated["readme"]})
    assert status == 400 and "nothing was saved" in data["error"]
    assert any(finding["severity"] == "ERROR" for finding in data["findings"])
    assert not (root / "scenarios/SZZ-0002").exists()
    assert (root / "scenarios/index.yml").read_bytes() == (ROOT / "scenarios/index.yml").read_bytes()


INDEX_ENTRY = ["- id: SZZ-0002", "  title: New SZZ scenario", "  slug: new-szz-scenario", "  category_code: S1",
               "  category: Basic semantic line changes", "  factors:", "  - single-bic", "  - single-bfc",
               "  - line-modification", "  difficulty: medium", "  status: draft",
               "  path: scenarios/SZZ-0002/scenario.yml"]


def test_the_downloaded_files_pass_strict_lint_where_the_docs_put_them(server, tmp_path):
    base, root = server
    generated = _model(tmp_path, tier="control")
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": generated["yaml"], "readme": generated["readme"]},
                         endpoint="preview")
    assert status == 200 and data["findings"] == [], data
    # the download writes nothing into the repository
    assert not (root / "scenarios/SZZ-0002").exists()
    assert (root / "scenarios/index.yml").read_bytes() == (ROOT / "scenarios/index.yml").read_bytes()
    # placed by hand, as tools/scenario-editor/README.md says, with no readme --write step
    placed = tmp_path / "placed/scenarios/SZZ-0002"
    placed.mkdir(parents=True)
    (placed / "scenario.yml").write_text(data["scenarioYaml"], encoding="utf-8")
    (placed / "README.md").write_text(data["readme"], encoding="utf-8")
    completed = _cli("validate", "--lint", "--strict", str(placed / "scenario.yml"))
    assert completed.returncode == 0, completed.stdout
    assert data["indexEntry"].splitlines() == INDEX_ENTRY


def test_the_download_refuses_what_the_save_refuses(server, tmp_path):
    base, root = server
    untiered = _model(tmp_path)
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": untiered["yaml"], "readme": untiered["readme"]},
                         endpoint="preview")
    assert status == 400 and "meta.tier" in data["error"]
    broken = _model(tmp_path, tier="control", bfc="c9")
    status, data = _post(base, {"id": "SZZ-0002", "scenarioYaml": broken["yaml"], "readme": broken["readme"]},
                         endpoint="preview")
    assert status == 400 and "nothing was rendered" in data["error"]
    assert any(finding["severity"] == "ERROR" for finding in data["findings"])
    assert not (root / "scenarios/SZZ-0002").exists()


def test_the_proposed_id_comes_after_every_retired_id(server):
    """docs/retired-ids.md retires SZZ-0167 at the highest, and the scratch copy
    has no scenario directory: an id is never issued twice (issue #112)."""
    base, _ = server
    with urllib.request.urlopen(f"{base}/api/scenarios", timeout=10) as response:
        assert json.loads(response.read())["nextId"] == "SZZ-0168"


def test_a_retired_id_is_neither_saved_nor_downloaded(server, tmp_path):
    base, root = server
    retired = _model(tmp_path, tier="control", scenarioId="SZZ-0058", repositoryName="SZZ-0058-new-szz-scenario")
    for endpoint in ("save", "preview"):
        status, data = _post(base, {"id": "SZZ-0058", "scenarioYaml": retired["yaml"], "readme": retired["readme"],
                                    "overwrite": True}, endpoint=endpoint)
        assert status == 409 and "SZZ-0058" in data["error"] and "docs/retired-ids.md" in data["error"], data
    assert not (root / "scenarios/SZZ-0058").exists()
    assert (root / "scenarios/index.yml").read_bytes() == (ROOT / "scenarios/index.yml").read_bytes()


def test_a_readme_without_its_header_is_ready_only_after_readme_write(tmp_path):
    # the path without the backend: the documented step is required, and enough
    generated = _model(tmp_path, tier="control")
    directory = tmp_path / "scenarios/SZZ-0002"
    directory.mkdir(parents=True)
    (tmp_path / "advanced-scenarios").mkdir()
    (directory / "scenario.yml").write_text(generated["yaml"], encoding="utf-8")
    (directory / "README.md").write_text(generated["readme"], encoding="utf-8")
    assert [finding["code"] for finding in _lint(directory / "scenario.yml")["findings"]] == ["W455"]
    written = _cli("readme", "--write", "--scenarios-root", str(tmp_path / "scenarios"),
                   "--advanced-scenarios-root", str(tmp_path / "advanced-scenarios"), str(directory))
    assert written.returncode == 0
    assert _cli("validate", "--lint", "--strict", str(directory / "scenario.yml")).returncode == 0
