"""Issue #24: the three "no ordinary BIC" contracts and the evaluation-policy families.

SZZG-0135 (external cause), SZZG-0136 (import boundary) and SZZG-0137 (authored initial
commit) state three different oracles for "the fix's deleted line belongs to the first
commit"; SZZG-0138/0139 join SZZG-0033 as the partial_credit family, SZZG-0140 joins
SZZG-0096/0115 as the top_k family, SZZG-0141/0142 join SZZG-0022 as the
relaxed_with_credit family. Every README states which answers pass and which fail;
these tests run the evaluator on exactly those answers against the generated commit maps,
and check the twin, blame and behaviour claims the READMEs make.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from szzbench.evaluator import Prediction, evaluate_scenario  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "advanced-scenarios"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def _generate(tmp_path: Path, sid: str) -> tuple[dict, dict, Path]:
    path = GRAPH / sid / "scenario.graph.yml"
    out = tmp_path / sid
    commit_map, verify = generate_graph_repository(path, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return yaml.safe_load(path.read_text(encoding="utf-8")), commit_map, out / "repo"


def _evaluate(sid: str, scenario: dict, commit_map: dict, answer: list[str], *, ranks: list[int] | None = None, variant: str | None = None) -> dict:
    predictions = [Prediction(scenario_id=sid, inducing_commit=c, rank=(ranks[i] if ranks else None)) for i, c in enumerate(answer)]
    return evaluate_scenario(sid, scenario, GRAPH / sid / "scenario.graph.yml", "advanced-scenarios", commit_map, predictions,
                             evaluation_variant=variant).to_dict()


# --- the three contracts ------------------------------------------------------

def test_external_cause_passes_only_for_the_empty_answer(tmp_path):
    scenario, cmap, _ = _generate(tmp_path, "SZZG-0135")
    empty = _evaluate("SZZG-0135", scenario, cmap, [])
    assert empty["status"] == "PASS" and empty["expect_no_bic"] is True
    blamed = _evaluate("SZZG-0135", scenario, cmap, ["c0"])
    assert blamed["status"] == "FAIL" and blamed["false_positives"] == ["c0"] and blamed["known_distractor_hits"] == ["c0"]


def test_import_boundary_is_empty_by_default_and_c0_under_the_boundary_variant(tmp_path):
    scenario, cmap, _ = _generate(tmp_path, "SZZG-0136")
    default = _evaluate("SZZG-0136", scenario, cmap, [])
    assert default["status"] == "PASS"
    # commit_level is the default without a note: the scenario no longer names a variant it lacks (GE129)
    assert default["evaluation_variant"] is None
    assert not any("evaluation variant" in note for note in default["result_notes"])
    assert _evaluate("SZZG-0136", scenario, cmap, ["c0"])["status"] == "FAIL"
    assert _evaluate("SZZG-0136", scenario, cmap, ["c0"], variant="boundary-commit")["status"] == "PASS"
    assert _evaluate("SZZG-0136", scenario, cmap, [], variant="boundary-commit")["status"] == "FAIL"


def test_authored_initial_commit_is_the_bic(tmp_path):
    scenario, cmap, _ = _generate(tmp_path, "SZZG-0137")
    assert _evaluate("SZZG-0137", scenario, cmap, ["c0"])["status"] == "PASS"
    assert _evaluate("SZZG-0137", scenario, cmap, [])["status"] == "FAIL"


def test_boundary_twins_differ_only_in_c0_message_and_import_md(tmp_path):
    """SZZG-0136 and SZZG-0137: same authors, dates and messages from c1 on, same source tree;
    only c0's message and docs/IMPORT.md tell them apart — and that is what decides the oracle."""
    _, a, repo_a = _generate(tmp_path, "SZZG-0136")
    _, b, repo_b = _generate(tmp_path, "SZZG-0137")
    assert set(a) == set(b) == {"c0", "c1", "c2", "c3"}
    for cid in a:
        for key in ("author", "author_date", "committer_date"):
            assert a[cid][key] == b[cid][key], (cid, key)
        assert (a[cid]["message"] == b[cid]["message"]) == (cid != "c0"), cid
    tree = lambda repo: {line.split("\t")[1]: line.split()[2] for line in _git(repo, "ls-tree", "-r", "HEAD").splitlines()}
    ta, tb = tree(repo_a), tree(repo_b)
    assert set(ta) - set(tb) == {"docs/IMPORT.md"} and set(tb) - set(ta) == set()
    assert all(ta[p] == tb[p] for p in tb), "a blob other than docs/IMPORT.md differs between the twins"
    for repo in (repo_a, repo_b):
        deleted = _git(repo, "diff", "-U0", "HEAD^", "HEAD")
        assert "-        return daysLate * centsPerDay;" in deleted
        blamed = _git(repo, "blame", "-l", "-s", "-L", "13,13", "HEAD^", "--", "src/main/java/example/billing/LateFee.java").split()[0]
        # git marks the root commit with ^ (its own word for a boundary) in place of the hash's first character
        expected = (a if repo is repo_a else b)["c0"]["hash"]
        assert blamed.startswith("^") and expected.startswith(blamed[1:]) and len(blamed) == 40


# --- partial_credit -----------------------------------------------------------

def test_partial_credit_majority_threshold(tmp_path):
    scenario, cmap, repo = _generate(tmp_path, "SZZG-0138")
    two = _evaluate("SZZG-0138", scenario, cmap, ["c1", "c2"])
    assert two["status"] == "PASS" and two["false_negatives"] == ["c3"]
    assert two["weighted_credit"] == 2.0 and two["possible_credit"] == 3.0
    assert _evaluate("SZZG-0138", scenario, cmap, ["c1"])["status"] == "FAIL"
    assert _evaluate("SZZG-0138", scenario, cmap, ["c1", "c2", "c3"])["status"] == "PASS"
    assert _evaluate("SZZG-0138", scenario, cmap, ["c1", "c2", "c0"])["status"] == "FAIL"
    # plain blame finds exactly the two modified lines, so it is the passing partial answer
    deleted = [l for l in _git(repo, "diff", "-U0", f"{cmap['c4']['hash']}^", cmap["c4"]["hash"]).splitlines() if l.startswith("-") and not l.startswith("---")]
    assert len(deleted) == 2
    by_hash = {e["hash"]: c for c, e in cmap.items()}
    blamed = set()
    for line in (9, 13):
        blamed.add(by_hash[_git(repo, "blame", "-l", "-s", "-L", f"{line},{line}", f"{cmap['c4']['hash']}^", "--", "src/main/java/example/pricing/Discounts.java").split()[0].lstrip("^")])
    assert blamed == {"c1", "c2"}


def test_partial_credit_across_a_merge(tmp_path):
    scenario, cmap, repo = _generate(tmp_path, "SZZG-0139")
    for answer in (["m1"], ["f1"], ["m1", "f1"]):
        assert _evaluate("SZZG-0139", scenario, cmap, answer)["status"] == "PASS", answer
    for answer in (["c2"], ["m1", "c2"], []):
        assert _evaluate("SZZG-0139", scenario, cmap, answer)["status"] == "FAIL", answer
    first_parent = {cmap_id for cmap_id, e in cmap.items() if e["hash"] in _git(repo, "rev-list", "--first-parent", cmap["c3"]["hash"]).split()}
    assert first_parent == {"c3", "c2", "m1", "c0"}, "a first-parent walk must not see the feature BIC"


# --- top_k --------------------------------------------------------------------

def test_top_k_strict_status_differs_from_szzg_0115_only_in_status_k(tmp_path):
    strict, cmap_s, repo = _generate(tmp_path, "SZZG-0140")
    lenient, cmap_l, _ = _generate(tmp_path, "SZZG-0115")
    assert strict["expected_szz"]["commit_level"]["status_k"] == 1
    assert "status_k" not in lenient["expected_szz"]["commit_level"]
    assert strict["expected_szz"]["commit_level"]["k_values"] == lenient["expected_szz"]["commit_level"]["k_values"] == [1, 3, 5]
    # the blame-recency ranking: the reformatting commit first, the BIC second
    ranked_strict = _evaluate("SZZG-0140", strict, cmap_s, ["c2", "c1"], ranks=[1, 2])
    assert ranked_strict["status"] == "FAIL" and ranked_strict["top_k"]["status_k"] == 1
    assert ranked_strict["top_k"]["hit_at"] == {"1": False, "3": True, "5": True}
    assert _evaluate("SZZG-0140", strict, cmap_s, ["c1", "c2"], ranks=[1, 2])["status"] == "PASS"
    distractor_first = [c for c in ("c2", "c3", "c1")]          # SZZG-0115's own noise commits ahead of its BIC
    assert _evaluate("SZZG-0115", lenient, cmap_l, distractor_first, ranks=[1, 2, 3])["status"] == "PASS"
    by_hash = {e["hash"]: c for c, e in cmap_s.items()}
    blamed = _git(repo, "blame", "-l", "-s", "-L", "6,6", f"{cmap_s['c4']['hash']}^", "--", "src/main/java/example/alerts/Threshold.java").split()[0]
    assert by_hash[blamed] == "c2"


# --- relaxed_with_credit --------------------------------------------------------

def test_relaxed_credit_saturates_without_full_recall(tmp_path):
    scenario, cmap, _ = _generate(tmp_path, "SZZG-0141")
    assert _evaluate("SZZG-0141", scenario, cmap, ["c3", "c4"])["status"] == "PASS"
    assert _evaluate("SZZG-0141", scenario, cmap, ["c3", "c4", "c1"])["status"] == "FAIL"     # default: origins are false positives
    v = "relaxed-with-credit"
    full = _evaluate("SZZG-0141", scenario, cmap, ["c3", "c4", "c1", "c2"], variant=v)
    assert full["status"] == "PASS" and full["weighted_credit"] == 2.0 and full["possible_credit"] == 2.0
    saturated = _evaluate("SZZG-0141", scenario, cmap, ["c3", "c1", "c2"], variant=v)
    assert saturated["status"] == "FAIL" and saturated["false_negatives"] == ["c4"]
    assert saturated["weighted_credit"] == 2.0, "1 direct + 2 x 0.5 reaches the cap although a required commit is missing"
    origins_only = _evaluate("SZZG-0141", scenario, cmap, ["c1", "c2"], variant=v)
    assert origins_only["status"] == "FAIL" and origins_only["weighted_credit"] == 1.0


def test_relaxed_credit_full_origin_fills_the_metric_but_not_the_status(tmp_path):
    scenario, cmap, _ = _generate(tmp_path, "SZZG-0142")
    assert _evaluate("SZZG-0142", scenario, cmap, ["c2"])["status"] == "PASS"
    assert _evaluate("SZZG-0142", scenario, cmap, ["c1"])["status"] == "FAIL"
    v = "relaxed-with-credit"
    origin = _evaluate("SZZG-0142", scenario, cmap, ["c1"], variant=v)
    assert origin["status"] == "FAIL" and origin["weighted_credit"] == 1.0 and origin["possible_credit"] == 1.0
    both = _evaluate("SZZG-0142", scenario, cmap, ["c2", "c1"], variant=v)
    assert both["status"] == "PASS" and both["weighted_credit"] == 1.0
    aware = _evaluate("SZZG-0142", scenario, cmap, ["c1"], variant="origin-aware")
    assert aware["status"] == "FAIL" and aware["weighted_credit"] == 0.5          # D3 keeps the suite's 0.5 convention


# --- behaviour: the external cause really is the environment ---------------------

@pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")
def test_external_cause_depends_on_the_locale_not_on_a_commit(tmp_path):
    """SZZG-0135: before the fix the amount cell follows the default locale; after it, it does not."""
    _, cmap, repo = _generate(tmp_path, "SZZG-0135")
    driver = 'public class Driver { public static void main(String[] a) { System.out.print(new example.report.CsvExport().amountCell(12.5)); } }'

    def run(cid: str, *props: str) -> str:
        work = tmp_path / f"run-{cid}-{'-'.join(props) or 'default'}"
        work.mkdir()
        tar = subprocess.run(["git", "archive", cmap[cid]["hash"]], cwd=repo, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
        (work / "Driver.java").write_text(driver)
        sources = [str(p) for p in work.rglob("*.java")]
        subprocess.run(["javac", "-d", str(work / "out"), *sources], check=True, capture_output=True)
        return subprocess.run(["java", *props, "-cp", str(work / "out"), "Driver"], capture_output=True, text=True, check=True).stdout

    de = ("-Duser.language=de", "-Duser.country=DE")
    en = ("-Duser.language=en", "-Duser.country=US")
    assert [run(c, *de) for c in ("c0", "c1", "c2", "c3")] == ["12,50", "12,50", "12,50", "12.50"]
    assert [run(c, *en) for c in ("c0", "c1", "c2", "c3")] == ["12.50", "12.50", "12.50", "12.50"]
