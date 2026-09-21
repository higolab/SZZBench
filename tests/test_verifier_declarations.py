"""The verifiers honour the same rewrite declaration the validator's W320 honours.

A scenario whose point is that the faulty line was rewritten before the fix
(SZZ-0081-0083 with `formatting-after-bic`, SZZG-0130/0132 with
`rewrite-after-bic`) cannot have its fault statement at BFC^. Reporting that as
a warning made `verify --strict` fail on exactly the property the scenario
declares; it is information, and the declaration is what makes it so.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402
from szzbench.graph_verifier import verify_graph_generated_repo  # noqa: E402
from szzbench.verifier import verify_generated_repo  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _codes(result):
    return sorted(f.code for f in result.findings if f.code in {"GW701", "GI701", "W700", "I701"})


def test_graph_verifier_reports_a_declared_rewrite_as_information(tmp_path):
    scenario = ROOT / "advanced-scenarios" / "SZZG-0130" / "scenario.graph.yml"
    out = tmp_path / "g"
    generate_graph_repository(scenario, out, force=True)
    result = verify_graph_generated_repo(out / "repo", scenario)
    assert not result.has_errors(), result.to_dict()
    assert _codes(result) == ["GI701"], _codes(result)


def test_classic_verifier_reports_a_declared_rewrite_as_information(tmp_path):
    scenario = ROOT / "scenarios" / "SZZ-0081" / "scenario.yml"   # declares formatting-after-bic
    out = tmp_path / "c"
    generate_repository(scenario, out, force=True)
    result = verify_generated_repo(out / "repo", scenario)
    assert not result.has_errors(), result.to_dict()
    assert _codes(result) == ["I701"], _codes(result)
