"""The verifiers honour the same rewrite declaration the validator's W320 honours.

A scenario whose point is that the faulty line was rewritten before the fix
(SZZ-0081-0083 with `formatting-after-bic`, SZZG-0130/0132 with
`rewrite-after-bic`) cannot have its fault statement at BFC^. Reporting that as
a warning made `verify --strict` fail on exactly the property the scenario
declares; it is information, and the declaration is what makes it so.  Without
the declaration it is W701 / GW701; the classic verifier reported it as W700
until issue #275.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from szzbench.generator import generate_repository
from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_verifier import verify_graph_generated_repo
from szzbench.validator import FAULT_REWRITE_FACTOR_RE
from szzbench.verifier import verify_generated_repo

ROOT = Path(__file__).resolve().parent.parent


def _codes(result):
    return sorted(f.code for f in result.findings if f.code in {"GW701", "GI701", "W701", "I701"})


def test_graph_verifier_reports_a_declared_rewrite_as_information(tmp_path):
    scenario = ROOT / "advanced-scenarios" / "SZZG-0130" / "scenario.graph.yml"
    out = tmp_path / "g"
    generate_graph_repository(scenario, out, force=True)
    result = verify_graph_generated_repo(out / "repo", scenario)
    assert not result.has_errors(), result.to_dict()
    assert _codes(result) == ["GI701"], _codes(result)


def test_classic_verifier_reports_a_declared_rewrite_as_information_and_an_undeclared_one_as_w701(tmp_path):
    scenario = ROOT / "scenarios" / "SZZ-0081" / "scenario.yml"   # declares formatting-after-bic
    out = tmp_path / "c"
    generate_repository(scenario, out, force=True)
    result = verify_generated_repo(out / "repo", scenario)
    assert not result.has_errors(), result.to_dict()
    assert _codes(result) == ["I701"], _codes(result)

    data = yaml.safe_load(scenario.read_text(encoding="utf-8"))           # the same, without the declaration
    data["meta"]["factors"] = [f for f in data["meta"]["factors"] if not FAULT_REWRITE_FACTOR_RE.search(f)]
    undeclared = tmp_path / "scenario.yml"
    undeclared.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = verify_generated_repo(out / "repo", undeclared)
    assert not result.has_errors(), result.to_dict()
    assert _codes(result) == ["W701"], _codes(result)
