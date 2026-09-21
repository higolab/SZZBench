"""Generated output left behind by a retired scenario must not fail a run.

Retiring a scenario removes its source and index entry, but the generated
repositories are untracked derived output, so an existing checkout keeps
`generated-input-repos/<id>/` and nothing regenerates or removes it.  Review of
PR #54 showed `szzbench baselines` exiting 1 on such a checkout with
"Cannot find scenario for 'SZZ-0058'", and `generate-all-repos --overwrite`
not helping because it visits only scenario files.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import yaml  # noqa: E402

from szzbench.baselines import run_baselines  # noqa: E402
from szzbench.bulk_generator import generate_all_repositories  # noqa: E402
from szzbench.evaluator import evaluate_prediction_map, evaluate_predictions  # noqa: E402
from szzbench.generator import generate_repository  # noqa: E402

JAVA = "src/main/java/example/Range.java"
OK = "package example;\npublic class Range {\n  boolean a(int x, int lo) { return x >= lo; }\n}\n"
BAD = OK.replace("x >= lo", "x > lo")


def _scenario(sid: str) -> dict:
    def commit(cid, body, role):
        return {"id": cid, "message": f"commit {cid}", "role": role,
                "operations": [{"type": "write_file", "path": JAVA, "content": body}]}
    return {
        "schema_version": "1.0",
        "meta": {"id": sid, "title": "Fixture", "category": "fixture", "category_code": "S1",
                 "tier": "control", "factors": ["single-bic"]},
        "repository": {"name": sid.lower(), "default_branch": "main", "language": "java"},
        "commits": [commit("c0", OK, "initial"), commit("c1", BAD, "bug_introducing"), commit("c2", OK, "bug_fixing")],
        "bugs": [{"id": "B001", "bug_fixing_commit": "c2", "bug_introducing_commits": ["c1"],
                  "fault": {"commit": "c1", "file": JAVA, "statement": "return x > lo;", "change_type": "line_modification"},
                  "fix": {"commit": "c2", "file": JAVA, "statement": "return x >= lo;", "fix_type": "line_modification"},
                  "expected_szz": {"commit_level": {"true_positives": ["c1"], "false_positives_allowed": []}}}],
    }


def _checkout(tmp_path: Path) -> tuple[Path, Path, Path]:
    """One live scenario with generated output, plus the leftover of a retired one."""
    scenarios = tmp_path / "scenarios"
    advanced = tmp_path / "advanced-scenarios"
    advanced.mkdir()
    repos = tmp_path / "generated-input-repos"
    live = scenarios / "SZZ-9001" / "scenario.yml"
    live.parent.mkdir(parents=True)
    live.write_text(yaml.safe_dump(_scenario("SZZ-9001"), sort_keys=False), encoding="utf-8")
    generate_repository(live, repos / "SZZ-9001" / "default", force=True)

    orphan = repos / "SZZ-9999" / "default"
    (orphan / "metadata").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(orphan / "repo")], check=True)
    (orphan / "metadata" / "commit-map.json").write_text(json.dumps({"commits": {}}), encoding="utf-8")
    return scenarios, advanced, repos


def test_baselines_skips_an_orphan_with_a_warning(tmp_path):
    scenarios, advanced, repos = _checkout(tmp_path)
    report = run_baselines(generated_root=repos, scenarios_root=scenarios, advanced_scenarios_root=advanced)
    assert report["errors"] == []
    assert report["scenario_count"] == 1
    assert len(report["warnings"]) == 1 and "SZZ-9999" in report["warnings"][0]
    assert "retired" in report["warnings"][0]


def test_evaluate_include_generated_skips_an_orphan_but_a_named_id_is_still_an_error(tmp_path):
    scenarios, advanced, repos = _checkout(tmp_path)
    common = dict(generated_root=repos, scenarios_root=scenarios, advanced_scenarios_root=advanced)

    walked = evaluate_predictions(None, include_generated=True, **common)
    assert walked.errors == []
    assert [e.scenario_id for e in walked.scenarios] == ["SZZ-9001"]
    assert any("SZZ-9999" in w for w in walked.warnings)

    # naming the id in the predictions is a claim about a scenario, not a leftover
    named = evaluate_prediction_map({}, explicit_scenarios={"SZZ-9999"}, **common)
    assert any("SZZ-9999" in e for e in named.errors)


def test_generate_all_reports_orphans_without_touching_them(tmp_path):
    scenarios, advanced, repos = _checkout(tmp_path)
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced,
                                       output_root=repos, overwrite=True, verify=False)
    assert result.failed_count == 0
    assert result.orphans == [repos.resolve() / "SZZ-9999"]
    assert (repos / "SZZ-9999" / "default" / "repo" / ".git").exists(), "reporting must not delete"


def test_coverage_skips_an_orphan_with_a_warning(tmp_path):
    from szzbench.coverage import run_coverage
    scenarios, advanced, repos = _checkout(tmp_path)
    report = run_coverage(generated_root=repos, scenarios_root=scenarios, advanced_scenarios_root=advanced)
    assert report["errors"] == []
    assert len(report["warnings"]) == 1 and "SZZ-9999" in report["warnings"][0]
