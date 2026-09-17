"""Evaluator semantics covered by GitHub issue #15.

These tests pin down the role vocabulary, the overall ``top_k`` status, the
missing-oracle fallback and ``expect_no_bic``, the ``known_distractors``
diagnostic, and the fix-shape classification.
"""

from pathlib import Path
import json
import subprocess
import sys
import textwrap

import pytest

from szzbench.evaluator import Prediction, evaluate_scenario
from szzbench.graph_scenario import DIRECT_BIC_ROLES, graph_bic_entries, normalize_bic_role
from szzbench.graph_verifier import verify_graph_generated_repo

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMIT_MAP = {"c0": {"hash": "0" * 40}, "c1": {"hash": "1" * 40}, "c2": {"hash": "2" * 40}, "c3": {"hash": "3" * 40}}


def _evaluate_graph(scenario, predictions, tmp_path, *, evaluation_variant=None, commit_map=COMMIT_MAP):
    return evaluate_scenario(
        "SZZG-test",
        scenario,
        tmp_path / "scenario.graph.yml",
        "advanced-scenarios",
        commit_map,
        [Prediction(scenario_id="SZZG-test", **kwargs) for kwargs in predictions],
        evaluation_variant=evaluation_variant,
    )


def _generate_graph_scenario(scenario_path: Path, out: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "generate-graph", str(scenario_path), "--out", str(out), "--force", "--no-verify"],
        check=True,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# --------------------------------------------------------------------------- #
# Task 1: role vocabulary
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (None, "direct"),
        ("", "direct"),
        ("direct", "direct"),
        ("direct_squash_bic", "direct"),
        ("merge_introducing", "direct"),
        ("bug_introducing", "direct"),
        ("DIRECT", "direct"),
        ("origin", "origin"),
        ("origin_bic", "origin"),
        ("old_origin_bic", "origin"),
        ("origin_bug_introducing", "origin"),
        ("reintroducing", "reintroducing"),
        ("direct_reintroduction", "reintroducing"),
        ("related_reintroducing", "reintroducing"),
        ("bug_reintroducing", "reintroducing"),
        ("contributing", "contributing"),
        ("contributing_bic", "contributing"),
        ("distractor", "other"),
        ("refactoring", "other"),
        (42, "other"),
    ],
)
def test_normalize_bic_role(role, expected):
    assert normalize_bic_role(role) == expected


def test_graph_bic_entries_filters_by_normalized_role():
    bug = {
        "bug_introducing_commits": [
            "c0",
            {"commit": "c1", "role": "merge_introducing"},
            {"commit": "c2", "role": "old_origin_bic"},
            {"commit": "c3", "role": "related_reintroducing"},
        ]
    }
    assert [entry["commit"] for entry in graph_bic_entries(bug)] == ["c0", "c1", "c2", "c3"]
    assert [entry["commit"] for entry in graph_bic_entries(bug, roles=DIRECT_BIC_ROLES)] == ["c0", "c1", "c3"]
    assert [entry["commit"] for entry in graph_bic_entries(bug, roles={"origin"})] == ["c2"]


def test_inferred_required_set_recognises_merge_introducing_role(tmp_path):
    scenario = {
        "meta": {"category": "roles"},
        "bugs": [
            {
                "id": "B001",
                "bug_introducing_commits": [
                    {"commit": "c3", "role": "merge_introducing"},
                    {"commit": "c1", "role": "origin_bic"},
                ],
            }
        ],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set"}},
    }
    result = _evaluate_graph(scenario, [{"inducing_commit": "c3"}], tmp_path)
    assert result.expected_bics == ["c3"]
    assert result.status == "PASS"


def test_verifier_basic_blame_accepts_merge_introducing_role(tmp_path):
    scenario_path = REPO_ROOT / "advanced-scenarios" / "SZZG-0045" / "scenario.graph.yml"
    out = tmp_path / "generated"
    _generate_graph_scenario(scenario_path, out)

    result = verify_graph_generated_repo(out / "repo", scenario_path)

    codes = [finding.code for finding in result.findings]
    assert "GW703" not in codes
    assert "GI703" in codes
