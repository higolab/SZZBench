"""Scenario metadata nothing checked: commit roles, the history summary, defeats and status.

* **Commit roles (issue #195).** `decisions/vocabulary.md` §2.2 made one list
  of commit roles canonical for both suites, but only the classic validator
  checked it (E030): `validate-graph --strict --lint` accepted any string, and
  28 commits of the graph suite kept 16 other spellings.  The list is
  `ALLOWED_ROLES`, extended with §2.2's five additions, and GE405 checks it.
* **`graph.history_summary` (issue #178).** Nothing read the summary, and
  SZZG-0128 kept its twin's `c3: merge feature branch into main` with no `c3`.
  GW456 reports a line that names a commit the scenario does not define.
* **`meta.defeats` (issue #207).** W462 / GW462 checked `defeats` only when it
  was present, and eighteen `discriminating` scenarios declared none.
* **`meta.status` (issue #157).** No check read it; W002 / GW018 now do.
"""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path

import yaml

from szzbench.graph_validator import lint_graph_scenario, validate_graph_static
from szzbench.validator import ALLOWED_ROLES, DEFEATABLE_FAMILIES, lint_scenario, validate_static

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


CLASSIC = _load("scenarios/SZZ-0005/scenario.yml")
GRAPH = _load("advanced-scenarios/SZZG-0001/scenario.graph.yml")
#: the fast-forward twin of SZZG-0043: commits c0, c1, c2 and c4, no c3 (issue #178)
FAST_FORWARD = _load("advanced-scenarios/SZZG-0128/scenario.graph.yml")


def _findings(result, code: str) -> list[tuple[str, str, str | None]]:
    return [(f.severity, f.code, f.location) for f in result.findings if f.code == code]


def test_a_graph_commit_role_outside_the_shared_list_is_ge405():
    data = deepcopy(GRAPH)
    data["commits"][1]["role"] = "other"                       # an old spelling §2.2 maps to intermediate
    assert not validate_graph_static(data).has_errors()        # a lint: generate-graph is not stopped
    assert _findings(lint_graph_scenario(data), "GE405") == [("ERROR", "GE405", "commits[1].role")]
    data["commits"][1]["role"] = "intermediate"
    assert _findings(lint_graph_scenario(data), "GE405") == []
    # the list is shared: the classic suite accepts §2.2's additions too
    classic = deepcopy(CLASSIC)
    classic["commits"][1]["role"] = "intermediate"
    assert _findings(validate_static(classic), "E030") == []


def test_vocabulary_section_2_2_names_the_roles_the_validators_accept():
    text = (ROOT / "docs/decisions/vocabulary.md").read_text(encoding="utf-8")
    section = text[text.index("### 2.2 Commit roles"):text.index("## 3. Categories")]
    listed = section[:section.index("(issue #18)")]
    assert set(re.findall(r"`([a-z_]+)`", listed)) == ALLOWED_ROLES


def test_a_history_summary_line_that_names_no_commit_is_gw456():
    data = deepcopy(FAST_FORWARD)
    assert _findings(lint_graph_scenario(data), "GW456") == []
    data["graph"]["history_summary"] += "\n\nc3: merge feature branch into main"
    [finding] = [f for f in lint_graph_scenario(data).findings if f.code == "GW456"]
    assert (finding.severity, finding.location) == ("WARNING", "graph.history_summary")
    assert "'c3'" in finding.message and "['c0', 'c1', 'c2', 'c4']" in finding.message
    # the placeholder new-graph-scenario writes is not a commit
    data["graph"]["history_summary"] = "TODO: Summarize the intended commit graph.\n"
    assert _findings(lint_graph_scenario(data), "GW456") == []


def test_a_discriminating_scenario_without_defeats_is_w462_and_gw462():
    classic = _load("scenarios/SZZ-0212/scenario.yml")
    assert classic["meta"]["tier"] == "discriminating"
    assert _findings(lint_scenario(classic, None), "W462") == []
    del classic["meta"]["defeats"]
    assert _findings(lint_scenario(classic, None), "W462") == [("WARNING", "W462", "meta.defeats")]
    classic["meta"]["tier"] = "control"                         # optional for a control
    assert _findings(lint_scenario(classic, None), "W462") == []

    graph = _load("advanced-scenarios/SZZG-0069/scenario.graph.yml")
    del graph["meta"]["defeats"]
    assert _findings(lint_graph_scenario(graph), "GW462") == [("WARNING", "GW462", "meta.defeats")]


def test_every_discriminating_scenario_declares_defeats_and_a_failure_mode():
    paths = [*ROOT.glob("scenarios/SZZ-*/scenario.yml"), *ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")]
    missing = []
    for path in sorted(paths):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data["meta"].get("tier") != "discriminating":
            continue
        failure_mode = (data.get("scenario_design") or {}).get("failure_mode") or ""
        if data["meta"].get("defeats") != list(DEFEATABLE_FAMILIES) or not failure_mode.startswith("A tool fails here when"):
            missing.append(path.parent.name)
    assert missing == []


def test_a_status_outside_the_vocabulary_is_w002_and_gw018():
    for value, expected in (("draft", []), ("retired", []), ("whatever", ["meta.status"]), (None, ["meta.status"])):
        classic, graph = deepcopy(CLASSIC), deepcopy(GRAPH)
        classic["meta"]["status"] = graph["meta"]["status"] = value
        assert [(s, loc) for s, _, loc in _findings(validate_static(classic), "W002")] == [("WARNING", loc) for loc in expected]
        assert [(s, loc) for s, _, loc in _findings(validate_graph_static(graph), "GW018")] == [("WARNING", loc) for loc in expected]
    del classic["meta"]["status"], graph["meta"]["status"]       # without the key there is nothing to check
    assert _findings(validate_static(classic), "W002") == [] and _findings(validate_graph_static(graph), "GW018") == []
