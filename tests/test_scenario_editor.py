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

from szzbench.generator import generate_repository

ROOT = Path(__file__).resolve().parents[1]

EDITOR = ROOT / "tools/scenario-editor"
MODEL = EDITOR / "src/scenarioModel.ts"

DRIVER = """
import * as model from %(model)s;
const overrides = JSON.parse(process.argv[2] || '{}');
const state = { ...model.initialState(), ...overrides };
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


def _model(tmp_path: Path, **overrides) -> dict:
    driver = tmp_path / "driver.mjs"
    driver.write_text(DRIVER % {"model": json.dumps(MODEL.as_uri())}, encoding="utf-8")
    completed = subprocess.run(["node", str(driver), json.dumps(overrides)], capture_output=True, text=True, check=True)
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
