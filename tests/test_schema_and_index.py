"""The keys of a graph scenario (issue #160) and the shape of the two index files (issue #200).

* #160: the graph loader kept every key and the checks read the ones they knew,
  some with a type check.  A misspelt key such as ``parent:`` was neither reported
  nor used, nine shipped scenarios carried keys nothing reads, ``allow_empty:
  "false"`` was true, ``bug_fixing_commits: c2`` was reported as missing,
  ``faults: {commit: no-such-commit}`` was skipped, and ``evaluation_policy: 5``
  passed.  An unknown key is now GW004, and the four types are GE077, GE085,
  GE107 and GE123.
* #200: ``advanced-scenarios/index.yml`` called itself a draft index and had a
  ``scenario_count`` and ``notes``, its entries had no ``slug`` or ``difficulty``,
  and the classic entries had no ``readme``.  IE046 compared a mirrored key only
  when the entry had it, so the graph index's ``slug`` and ``difficulty`` were
  never compared.  Both files now have one shape, which the builders write and
  ``validate-index`` checks.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from support import scenario_file
from szzbench import graph_validator
from szzbench.graph_scenario_builder import create_new_graph_scenario
from szzbench.graph_validator import validate_graph_scenario_file
from szzbench.scenario_builder import create_new_scenario
from szzbench.validator import validate_index_file

ROOT = Path(__file__).resolve().parents[1]
SZZG_0001 = yaml.safe_load(scenario_file("SZZG-0001").read_text(encoding="utf-8"))
#: The keys of an entry of either index, in their order (issue #200).
ENTRY_KEYS = ("id", "title", "slug", "category_code", "category", "factors", "difficulty", "status", "path", "readme")


def _write(tmp_path: Path, mutate) -> Path:
    data = yaml.safe_load(yaml.safe_dump(SZZG_0001))
    mutate(data)
    path = tmp_path / "SZZG-0001" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


# --- #160: unknown keys ------------------------------------------------------------------------

def test_an_unknown_key_is_a_warning_at_its_location_and_notes_are_free(tmp_path):
    def mutate(data):
        data["commits"][1]["parent"] = data["commits"][1].pop("parents")      # the misspelling of the issue
        data["meta"]["tittle"] = "typo"
        data["commits"][2]["operations"][1]["ocurrence"] = 1
        data["bugs"][0]["faults"][0]["statment"] = "typo"
        data["expected_szz"]["commit_level"]["requird"] = ["c1"]
        data["files"] = []                                                    # SZZG-0019's former top-level key
        # free-form: notes and x- keys, anywhere
        data["x-files"] = []
        data["commits"][0]["x-work_item"] = "WI-001"
        data["commits"][0]["notes"] = "a note"
        data["bugs"][0]["faults"][0]["x-encoding"] = "windows-1252"
    _, result = validate_graph_scenario_file(_write(tmp_path, mutate))
    unknown = {f.location: f for f in result.findings if f.code == "GW004"}
    assert sorted(unknown) == ["bugs[0].faults[0].statment", "commits[1].parent",
                               "commits[2].operations[1].ocurrence", "expected_szz.commit_level.requird",
                               "files", "meta.tittle"]
    assert all(f.severity == "WARNING" for f in unknown.values())
    assert unknown["commits[1].parent"].message.startswith(
        "Commit 'c1' has an unknown key 'parent' (did you mean 'parents'?), which nothing reads.")
    assert "(did you mean 'occurrence'?)" in unknown["commits[2].operations[1].ocurrence"].message
    assert "did you mean" not in unknown["files"].message
    assert "GE048" in [f.code for f in result.findings]                      # the missing parents, as before


def test_the_shipped_graph_scenarios_have_no_unknown_keys():
    paths = sorted((ROOT / "advanced-scenarios").glob("SZZG-*/scenario.graph.yml"))
    assert len(paths) == 146
    unknown = []
    for path in paths:
        _, result = validate_graph_scenario_file(path, strict_paths=True)
        unknown += [f"{path.parent.name}: {f.location}" for f in result.findings if f.code == "GW004"]
    assert unknown == []
    # the leftovers of the issue are notes now
    data = yaml.safe_load(scenario_file("SZZG-0093").read_text(encoding="utf-8"))
    assert [commit.get("x-work_item") for commit in data["commits"]] == [None, "WI-001", "WI-001", "WI-001", None]


def test_the_keys_of_docs_graph_schema_are_the_keys_the_validator_allows():
    """Each table of docs/graph-schema.md lists, in its first column, the keys of the object its heading names."""
    sections = re.split(r"^## ", (ROOT / "docs" / "graph-schema.md").read_text(encoding="utf-8"), flags=re.M)
    tables = {}
    for section in sections[1:]:
        heading, _, body = section.partition("\n")
        rows = [line.split("|")[1:-1] for line in body.splitlines() if line.startswith("| `")]
        tables[heading] = rows
    expected = {
        "Top level": graph_validator.TOP_LEVEL_KEYS,
        "`meta`": graph_validator.META_KEYS,
        "`repository`": graph_validator.REPOSITORY_KEYS,
        "`graph`": graph_validator.GRAPH_KEYS,
        "A commit": graph_validator.COMMIT_KEYS,
        "A bug": graph_validator.BUG_KEYS,
        "A fault or a fix": graph_validator.FAULT_KEYS | graph_validator.FIX_KEYS,
        "`expected_szz`": graph_validator.EXPECTED_SZZ_KEYS,
        "A `commit_level`": graph_validator.COMMIT_LEVEL_KEYS,
        "An evaluation variant": graph_validator.EVALUATION_VARIANT_KEYS,
        "A `branch_level` entry": graph_validator.BRANCH_LEVEL_KEYS,
    }
    for heading, keys in expected.items():
        listed = {key for row in tables[heading] for key in re.findall(r"`([^`]+)`", row[0])}
        assert listed == keys, heading
    operations = {re.findall(r"`([^`]+)`", row[0])[0]: set(re.findall(r"`([^`]+)`", row[1]))
                  for row in tables["An operation"]}
    assert operations == {op_type: set(keys) for op_type, keys in graph_validator.OPERATION_KEYS.items()}


# --- #160: loose types -------------------------------------------------------------------------

def _empty_commit(allow_empty):
    def mutate(data):
        data["commits"].insert(2, {"id": "c1b", "branch": "main", "parents": ["c1"], "message": "Nothing to see",
                                   "role": "cleanup", "operations": [], "allow_empty": allow_empty})
        data["commits"][3]["parents"] = ["c1b"]
    return mutate


@pytest.mark.parametrize("mutate, code, location, message", [
    (_empty_commit("false"), "GE077", "commits[2].allow_empty",
     "Commit 'c1b' allow_empty must be true or false, not 'false', which generation and the checks read as true."),
    (lambda d: d["bugs"][0].__setitem__("bug_fixing_commits", "c2"), "GE085", "bugs[0].bug_fixing_commits",
     "bug B001: bug_fixing_commits must be a list, not str."),
    (lambda d: d["bugs"][0].__setitem__("faults", {"commit": "no-such-commit"}), "GE107", "bugs[0].faults",
     "bug B001: faults must be a list of fault entries, not dict."),
    (lambda d: d["expected_szz"]["commit_level"].__setitem__("evaluation_policy", 5), "GE123",
     "expected_szz.commit_level.evaluation_policy",
     "evaluation_policy must be a string, the name of a policy such as 'exact_set', not int 5; the evaluator "
     "would score it as exact_set without a note."),
], ids=["allow_empty", "bug_fixing_commits", "faults", "evaluation_policy"])
def test_a_loose_type_is_an_error_that_names_the_type(tmp_path, mutate, code, location, message):
    _, result = validate_graph_scenario_file(_write(tmp_path, mutate), simulate=True)
    assert [(f.severity, f.code, f.location, f.message) for f in result.findings if f.severity != "INFO"] == [
        ("ERROR", code, location, message)]


# --- #200: the index files ---------------------------------------------------------------------

def test_both_index_files_have_one_shape():
    for suite in ("scenarios", "advanced-scenarios"):
        text = (ROOT / suite / "index.yml").read_text(encoding="utf-8")
        index = yaml.safe_load(text)
        assert list(index) == ["scenarios"], suite
        assert {tuple(entry) for entry in index["scenarios"]} == {ENTRY_KEYS}, suite
        assert "draft" not in text, suite


def test_validate_index_reports_a_missing_entry_key_and_a_key_outside_the_shape(tmp_path):
    root = tmp_path / "advanced-scenarios"
    (root / "SZZG-0001").mkdir(parents=True)
    meta = {"id": "SZZG-0001", "title": "Probe", "slug": "probe", "category_code": "G1", "category": "C",
            "factors": ["f"], "difficulty": "easy", "status": "active"}
    (root / "SZZG-0001" / "scenario.graph.yml").write_text(yaml.safe_dump({"meta": meta}), encoding="utf-8")
    (root / "SZZG-0001" / "README.md").write_text("# README\n", encoding="utf-8")
    # an entry of the former graph index: no slug, no difficulty; and its scenario_count
    entry = {key: meta[key] for key in ("id", "title", "category_code", "category", "factors", "status")}
    entry |= {"path": "advanced-scenarios/SZZG-0001/scenario.graph.yml", "readme": "advanced-scenarios/SZZG-0001/README.md"}
    (root / "index.yml").write_text(yaml.safe_dump({"scenario_count": 1, "scenarios": [entry]}, sort_keys=False),
                                    encoding="utf-8")
    result = validate_index_file(root / "index.yml", root, "scenario.graph.yml")
    prefix = (root / "index.yml").as_posix()
    assert [(f.severity, f.code, f.location) for f in result.findings] == [
        ("WARNING", "IW004", f"{prefix}:scenario_count"),
        ("ERROR", "IE046", f"{prefix}:scenarios[0].slug"),
        ("ERROR", "IE046", f"{prefix}:scenarios[0].difficulty"),
    ]


def test_both_builders_write_an_entry_of_the_shared_shape(tmp_path):
    for suite, create in (("scenarios", create_new_scenario), ("advanced-scenarios", create_new_graph_scenario)):
        root = tmp_path / suite
        root.mkdir()
        (root / "index.yml").write_bytes((ROOT / suite / "index.yml").read_bytes())
        result = create(title="Probe", category="G4" if suite == "advanced-scenarios" else "S3",
                        factors=["line-modification"], tier="control", root=root)
        index = yaml.safe_load(result.index_path.read_text(encoding="utf-8"))
        assert list(index) == ["scenarios"]
        entry = index["scenarios"][-1]
        assert tuple(entry) == ENTRY_KEYS
        assert (entry["slug"], entry["difficulty"], entry["readme"]) == (
            "probe", "medium", f"{suite}/{result.scenario_id}/README.md")
