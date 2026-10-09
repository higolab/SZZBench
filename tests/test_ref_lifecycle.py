"""``graph.ref_lifecycle`` is validated as the generator applies it (issue #229).

Only the generator read the section, after every commit existed, and
``validate-graph --simulate --strict --strict-paths --lint`` passed the nine
malformed values of the issue's table.  Six then failed ``generate-graph``,
three of them with Git's own message after earlier entries had changed the
refs.  Three generated and verified cleanly while meaning something else: a
misspelt ``delete_branch:`` and a value that was not an object were ignored,
and a tag named ``main`` made ``git log main`` show the tagged commit instead
of the branch tip.  Validation now reports each of them at the key or entry
(GE152-GE158), and the generator checks the same rules before it changes the
first ref.
"""
from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import szzbench.graph_generator as graph_generator
import szzbench.graph_scenario as graph_scenario
from support import git, git_env, scenario_file
from szzbench.findings import ValidationResult
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static

ROOT = Path(__file__).resolve().parents[1]
SZZG_0072 = yaml.safe_load(scenario_file("SZZG-0072").read_text(encoding="utf-8"))

# The rows of the issue's table: a copy of SZZG-0072 (branches main and feature; commits c0, f1, f2, r2, c3;
# `ref_lifecycle: {delete_branches: [feature]}`) with graph.ref_lifecycle replaced, and the one error it now gets.
CASES = {
    "unknown-branch": ({"delete_branches": ["nope"]},
                       "GE154", "graph.ref_lifecycle.delete_branches[0]"),
    "unknown-commit": ({"delete_branches": ["feature"], "tags": [{"name": "v1", "commit": "nope"}]},
                       "GE156", "graph.ref_lifecycle.tags[0].commit"),
    "tags-not-a-list": ({"delete_branches": ["feature"], "tags": "v1"},
                        "GE155", "graph.ref_lifecycle.tags"),
    "bad-tag-name": ({"delete_branches": ["feature"], "tags": [{"name": "v 1", "commit": "c0"}]},
                     "GE157", "graph.ref_lifecycle.tags[0].name"),
    "duplicate-tag": ({"delete_branches": ["feature"], "tags": [{"name": "v1", "commit": "c0"}, {"name": "v1", "commit": "c3"}]},
                      "GE158", "graph.ref_lifecycle.tags[1].name"),
    "duplicate-delete": ({"delete_branches": ["feature", "feature"]},
                         "GE153", "graph.ref_lifecycle.delete_branches[1]"),
    "typo-key": ({"delete_branch": ["feature"]},
                 "GE152", "graph.ref_lifecycle.delete_branch"),
    "not-a-mapping": (["feature"],
                      "GE152", "graph.ref_lifecycle"),
    "tag-named-like-branch": ({"delete_branches": ["feature"], "tags": [{"name": "main", "commit": "c0"}]},
                              "GE158", "graph.ref_lifecycle.tags[0].name"),
}


def _with_lifecycle(lifecycle) -> dict:
    data = copy.deepcopy(SZZG_0072)
    data["graph"]["ref_lifecycle"] = lifecycle
    return data


def _write(directory: Path, data: dict) -> Path:
    """The scenario as the issue's script writes it: SZZG-0072/scenario.graph.yml beside the README."""
    path = directory / "SZZG-0072" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (path.parent / "README.md").write_bytes((scenario_file("SZZG-0072").parent / "README.md").read_bytes())
    return path


def _errors(result: ValidationResult) -> list[tuple[str, str | None]]:
    return [(f.code, f.location) for f in result.findings if f.severity == "ERROR"]


def _lifecycle_findings(result: ValidationResult) -> list[tuple[str, str | None]]:
    return [(f.code, f.location) for f in result.findings if f.code in LIFECYCLE_CODES]


LIFECYCLE_CODES = {f"GE{n}" for n in range(152, 159)}


# --- the issue's table ----------------------------------------------------------

@pytest.mark.parametrize("case", list(CASES))
def test_each_row_of_the_table_is_an_error_at_its_key_or_entry(tmp_path, case):
    lifecycle, code, location = CASES[case]
    _, result = validate_graph_scenario_file(_write(tmp_path, _with_lifecycle(lifecycle)))     # no --simulate
    assert _errors(result) == [(code, location)]
    assert [f.severity for f in result.findings if f.code == code] == ["ERROR"]


@pytest.mark.parametrize("case", list(CASES))
def test_validate_graph_fails_on_them_from_a_relative_path(tmp_path, case):
    """The issue's command line, run from the directory that holds the copies."""
    lifecycle, code, location = CASES[case]
    _write(tmp_path / case, _with_lifecycle(lifecycle))
    relative = f"{case}/SZZG-0072/scenario.graph.yml"
    completed = subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "validate-graph", "--simulate", "--strict", "--strict-paths", "--lint", relative],
        cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert f"[ERROR] {code}: " in completed.stdout
    assert completed.stdout.splitlines()[0].endswith(f"({location})")
    assert "Summary: 1 error(s), 0 warning(s), 0 info item(s)" in completed.stdout


def test_the_messages_say_what_is_wrong():
    messages = {}
    for case, (lifecycle, code, _) in CASES.items():
        [finding] = [f for f in validate_graph_static(_with_lifecycle(lifecycle)).findings if f.code == code]
        messages[case] = finding.message
    assert messages["typo-key"] == "graph.ref_lifecycle has an unknown key 'delete_branch'; the key is 'delete_branches'."
    assert messages["not-a-mapping"] == ("graph.ref_lifecycle must be an object with the keys delete_branches and tags, "
                                         "not list.")
    assert messages["unknown-branch"] == ("graph.ref_lifecycle.delete_branches[0] names branch 'nope', which no commit "
                                          "is on (branches: feature, main).")
    assert messages["duplicate-delete"] == ("graph.ref_lifecycle.delete_branches[1] names branch 'feature' again (also "
                                            "graph.ref_lifecycle.delete_branches[0]); a branch is deleted once.")
    assert messages["bad-tag-name"] == ("graph.ref_lifecycle.tags[0].name 'v 1' is not a tag name Git accepts: "
                                        "it contains a space.")
    assert messages["duplicate-tag"] == ("graph.ref_lifecycle.tags[1].name 'v1' is the name of "
                                         "graph.ref_lifecycle.tags[0] as well; Git keeps one tag per name.")
    assert messages["tag-named-like-branch"].startswith(
        "graph.ref_lifecycle.tags[0].name 'main' is the name of the branch 'main': the name would be ambiguous, "
        "and Git reads a bare 'main' as the tag")


@pytest.mark.parametrize("case", list(CASES))
def test_generate_graph_refuses_them_at_validation(tmp_path, case):
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(_write(tmp_path, _with_lifecycle(CASES[case][0])), tmp_path / "out")
    assert not (tmp_path / "out").exists()


# --- more of each rule ----------------------------------------------------------------

MORE_CASES = {
    "blank section": (None, [("GE152", "graph.ref_lifecycle")]),
    "string section": ("feature", [("GE152", "graph.ref_lifecycle")]),
    "unknown key without a near miss": ({"delete_branches": ["feature"], "keep": True},
                                        [("GE152", "graph.ref_lifecycle.keep")]),
    "misspelt tags": ({"tag": [{"name": "v1", "commit": "c0"}]}, [("GE152", "graph.ref_lifecycle.tag")]),
    "blank delete_branches": ({"delete_branches": None}, [("GE153", "graph.ref_lifecycle.delete_branches")]),
    "delete_branches a string": ({"delete_branches": "feature"}, [("GE153", "graph.ref_lifecycle.delete_branches")]),
    "a branch that is not a string": ({"delete_branches": ["feature", 3]},
                                      [("GE153", "graph.ref_lifecycle.delete_branches[1]")]),
    "a branch in another letter case": ({"delete_branches": ["Feature"]},
                                        [("GE154", "graph.ref_lifecycle.delete_branches[0]")]),
    "blank tags": ({"tags": None}, [("GE155", "graph.ref_lifecycle.tags")]),
    "a tag that is a string": ({"tags": ["v1"]}, [("GE155", "graph.ref_lifecycle.tags[0]")]),
    "a tag without commit": ({"tags": [{"name": "v1"}]}, [("GE155", "graph.ref_lifecycle.tags[0].commit")]),
    "a tag whose name is a number": ({"tags": [{"name": 1.0, "commit": "c0"}]},
                                     [("GE155", "graph.ref_lifecycle.tags[0].name")]),
    "a tag with another key": ({"tags": [{"name": "v1", "commit": "c0", "message": "Release 1"}]},
                               [("GE155", "graph.ref_lifecycle.tags[0].message")]),
    "a tag with a misspelt key": ({"tags": [{"name": "v1", "commmit": "c0"}]},
                                  [("GE155", "graph.ref_lifecycle.tags[0].commmit"),
                                   ("GE155", "graph.ref_lifecycle.tags[0].commit")]),
    "a tag on a commit generator that is not planned": ({"tags": [{"name": "v1", "commit": "c0.g1"}]},
                                                        [("GE156", "graph.ref_lifecycle.tags[0].commit")]),
    "a tag named HEAD": ({"tags": [{"name": "HEAD", "commit": "c0"}]}, [("GE157", "graph.ref_lifecycle.tags[0].name")]),
    "a tag named like an option": ({"tags": [{"name": "-d", "commit": "c0"}]},
                                   [("GE157", "graph.ref_lifecycle.tags[0].name")]),
    "a tag below another": ({"tags": [{"name": "v1", "commit": "c0"}, {"name": "v1/rc", "commit": "c3"}]},
                            [("GE158", "graph.ref_lifecycle.tags[1].name")]),
    "a tag above another": ({"tags": [{"name": "v1/rc", "commit": "c0"}, {"name": "v1", "commit": "c3"}]},
                            [("GE158", "graph.ref_lifecycle.tags[1].name")]),
    "two tags in another letter case": ({"tags": [{"name": "v1", "commit": "c0"}, {"name": "V1", "commit": "c3"}]},
                                        [("GE158", "graph.ref_lifecycle.tags[1].name")]),
    "a tag named like a kept branch in another letter case": ({"tags": [{"name": "Main", "commit": "c0"}]},
                                                               [("GE158", "graph.ref_lifecycle.tags[0].name")]),
    "a tag named like the deleted branch": ({"delete_branches": ["feature"], "tags": [{"name": "feature", "commit": "f2"}]},
                                            [("GE158", "graph.ref_lifecycle.tags[0].name")]),
}


@pytest.mark.parametrize("case", list(MORE_CASES))
def test_each_rule_is_checked(case):
    lifecycle, expected = MORE_CASES[case]
    result = validate_graph_static(_with_lifecycle(lifecycle))
    assert _errors(result) == expected


def test_every_problem_of_a_section_is_reported_in_one_run():
    lifecycle = {"delete_branch": ["feature"], "delete_branches": ["nope", "nope"],
                 "tags": [{"name": "v 1", "commit": "zz"}, {"name": "main", "commit": "c0"}, 5]}
    assert _errors(validate_graph_static(_with_lifecycle(lifecycle))) == [
        ("GE152", "graph.ref_lifecycle.delete_branch"),
        ("GE154", "graph.ref_lifecycle.delete_branches[0]"),
        ("GE153", "graph.ref_lifecycle.delete_branches[1]"),
        ("GE156", "graph.ref_lifecycle.tags[0].commit"),
        ("GE157", "graph.ref_lifecycle.tags[0].name"),
        ("GE158", "graph.ref_lifecycle.tags[1].name"),
        ("GE155", "graph.ref_lifecycle.tags[2]"),
    ]


def test_the_default_branch_counts_for_a_commit_without_branch():
    data = _with_lifecycle({"delete_branches": ["trunk"], "tags": [{"name": "trunk", "commit": "c0"}]})
    data["repository"]["default_branch"] = "trunk"
    for commit in data["commits"]:
        if commit["branch"] == "main":
            del commit["branch"]                     # on the default branch, trunk
    assert _errors(validate_graph_static(data)) == [("GE158", "graph.ref_lifecycle.tags[0].name")]


# --- what stays valid ---------------------------------------------------------------

@pytest.mark.parametrize("sid", ["SZZG-0072", "SZZG-0075", "SZZG-0122", "SZZG-0152"])
def test_the_shipped_lifecycles_are_valid(sid):
    data = yaml.safe_load(scenario_file(sid).read_text(encoding="utf-8"))
    assert "ref_lifecycle" in data["graph"]
    assert validate_graph_static(data).findings == []


def test_no_shipped_graph_scenario_has_a_lifecycle_finding():
    paths = sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml"))
    assert len(paths) >= 146
    with_lifecycle = 0
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        with_lifecycle += "ref_lifecycle" in (data.get("graph") or {})
        assert _lifecycle_findings(validate_graph_static(data)) == [], path
    assert with_lifecycle == 4


WELL_FORMED = {
    "empty": {},
    "empty lists": {"delete_branches": [], "tags": []},
    # the rebased-away originals stay reachable through a tag, as GW151's message suggests
    "a tag keeps the deleted branch's commits": {"delete_branches": ["feature"],
                                                 "tags": [{"name": "pre-rebase/feature", "commit": "f2"}]},
    "a tag below a branch name": {"tags": [{"name": "feature/v1", "commit": "f2"}, {"name": "main-v1", "commit": "c0"}]},
    "every branch deleted": {"delete_branches": ["feature", "main"]},
    "names Git accepts": {"tags": [{"name": "v2.3.0", "commit": "c0"}, {"name": "release/2024-01", "commit": "c3"},
                                   {"name": "@", "commit": "c0"}, {"name": "café", "commit": "c0"}]},
}


@pytest.mark.parametrize("case", list(WELL_FORMED))
def test_well_formed_lifecycles_pass(case):
    assert validate_graph_static(_with_lifecycle(WELL_FORMED[case])).findings == []


def test_a_well_formed_lifecycle_generates_as_written(tmp_path):
    lifecycle = WELL_FORMED["a tag keeps the deleted branch's commits"]
    commit_map, verify = generate_graph_repository(_write(tmp_path, _with_lifecycle(lifecycle)), tmp_path / "out")
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    repo = tmp_path / "out" / "repo"
    assert git(repo, "for-each-ref", "--format=%(refname)").split() == ["refs/heads/main", "refs/tags/pre-rebase/feature"]
    assert git(repo, "rev-parse", "pre-rebase/feature") == commit_map["f2"]["hash"]


def test_a_tag_may_name_a_generated_commit():
    """A tag may point into a commit_generator chain (gitutils.reachable_commit_ids models it, PR #64)."""
    data = _with_lifecycle({"delete_branches": ["feature"], "tags": [{"name": "catalog-snapshot", "commit": "f2.g2"}]})
    [f2] = [c for c in data["commits"] if c["id"] == "f2"]
    f2["operations"].insert(0, {"type": "commit_generator", "generator": "catalog_sync", "count": 3, "files": 1,
                                "path": "generated/catalog"})
    assert _errors(validate_graph_static(data)) == []
    f2["operations"][0]["count"] = 1
    assert _errors(validate_graph_static(data)) == [("GE156", "graph.ref_lifecycle.tags[0].commit")]


# --- the tag name rule is Git's -------------------------------------------------------

#: Names Git accepts and names it refuses as refs/tags/<name>; each refused one breaks one rule.
TAG_NAMES = [
    # accepted
    "v1", "v1.0", "v2.3.0", "pre-squash/feature", "pre-rebase/feature", "release/2024-01", "a.b", "a./b", "a/b.c",
    "@", "a@b", "@a", "a@", "@@", "{@", "@/x", "a{b", "a}b", "a]b", "a#b", "a$b", "a%b", "a&b", "a'b", 'a"b', "a(b)",
    "a+b", "a,b", "a;b", "a<b>", "a=b", "a|b", "a`b", "a!b", "a_b", "1", "a-", "a/-b", "x.lock.y", "lock", "a.lockx",
    "a-.lock-b", "x/lock", "FETCH_HEAD", "ORIG_HEAD", "refs/heads/main", "0123456789abcdef0123456789abcdef01234567",
    "héllo", "日本語", "ä/ö", "emoji😀", " nbsp",
    # refused
    "", " ", "v 1", "trailing ", " leading", "v\t1", "tab\there", "v\n1", "v\x01", "v\x1f", "v\x7f", "v~1", "v^1",
    "v:1", "v?1", "v*1", "v[1", "v\\1", "a..b", "..", ".", "...", ".v", "x/.y", "x/..", "a/./b", "a/../b", "v1.lock",
    "a/b.lock", "a.lock/b", ".lock", "v1.", "a.", "x.y.", "a/b.", "a./b.", "/a", "a/", "v1/", "a//b", "a@{b", "@{",
    "@{u}", "a@{", "a/@{b}",
]


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=git_env(), capture_output=True, text=True)


def test_tag_names_are_refused_exactly_where_git_check_ref_format_refuses_them(tmp_path):
    assert len(TAG_NAMES) >= 90
    mismatches = []
    for name in TAG_NAMES:
        git_accepts = _git(tmp_path, "check-ref-format", f"refs/tags/{name}").returncode == 0
        if git_accepts != (graph_scenario.tag_name_problem(name) is None):
            mismatches.append((name, "git accepts" if git_accepts else "git refuses", graph_scenario.tag_name_problem(name)))
    assert mismatches == []
    assert sum(graph_scenario.tag_name_problem(name) is None for name in TAG_NAMES) >= 40     # both kinds are compared


def test_git_tag_creates_every_name_szzbench_accepts(tmp_path):
    """The generator runs ``git tag <name> <hash>``, which adds two refusals to the ref format."""
    assert _git(tmp_path, "init", "-q", "--template=").returncode == 0
    assert _git(tmp_path, "-c", "user.name=a", "-c", "user.email=a@example.com",
                "commit", "-q", "--allow-empty", "-m", "c0").returncode == 0
    for name in [n for n in TAG_NAMES if graph_scenario.tag_name_problem(n) is None]:
        created = _git(tmp_path, "tag", name, "HEAD")
        assert created.returncode == 0, (name, created.stderr)
        assert _git(tmp_path, "tag", "-d", name).returncode == 0
    for name in ("-d", "-v1", "--list"):
        assert _git(tmp_path, "check-ref-format", f"refs/tags/{name}").returncode == 0
        assert "starts with '-'" in graph_scenario.tag_name_problem(name)
    # git tag HEAD: Git 2.50 refuses it, Git 2.39 creates refs/tags/HEAD; SZZBench refuses it everywhere
    assert graph_scenario.tag_name_problem("HEAD") == "it is HEAD, which recent versions of git tag refuse"


# --- the generator checks every entry before it changes a ref ---------------------------

# What generation said with validation bypassed, and the refs it had left: none of them is Git's message now,
# and the refs are those the commits left (main and feature, no tag).
GENERATOR_MESSAGES = {
    "unknown-branch": "graph.ref_lifecycle.delete_branches[0] names branch 'nope', which no commit is on "
                      "(branches: feature, main) (GE154). No ref was changed.",
    "bad-tag-name": "graph.ref_lifecycle.tags[0].name 'v 1' is not a tag name Git accepts: it contains a space (GE157). "
                    "No ref was changed.",
    "duplicate-tag": "graph.ref_lifecycle.tags[1].name 'v1' is the name of graph.ref_lifecycle.tags[0] as well; "
                     "Git keeps one tag per name (GE158). No ref was changed.",
    "duplicate-delete": "graph.ref_lifecycle.delete_branches[1] names branch 'feature' again (also "
                        "graph.ref_lifecycle.delete_branches[0]); a branch is deleted once (GE153). No ref was changed.",
    "typo-key": "graph.ref_lifecycle has an unknown key 'delete_branch'; the key is 'delete_branches' (GE152). "
                "No ref was changed.",
    "not-a-mapping": "graph.ref_lifecycle must be an object with the keys delete_branches and tags, not list (GE152). "
                     "No ref was changed.",
}


@pytest.mark.parametrize("case", list(CASES))
def test_the_generator_refuses_them_before_it_changes_a_ref(tmp_path, monkeypatch, case):
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))
    out = tmp_path / "out"
    with pytest.raises(GraphGenerationError) as excinfo:
        generate_graph_repository(_write(tmp_path, _with_lifecycle(CASES[case][0])), out)
    message = str(excinfo.value)
    assert f"({CASES[case][1]}). No ref was changed." in message
    assert "fatal:" not in message and "error:" not in message
    if case in GENERATOR_MESSAGES:
        assert message == GENERATOR_MESSAGES[case]
    assert git(out / "repo", "for-each-ref", "--format=%(refname)").split() == ["refs/heads/feature", "refs/heads/main"]
    assert not (out / "metadata" / "graph-map.json").exists()


def test_the_generator_counts_the_other_problems(tmp_path, monkeypatch):
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))
    lifecycle = {"delete_branches": ["feature", "feature"], "tags": [{"name": "v 1", "commit": "c0"}, {"name": "main", "commit": "zz"}]}
    with pytest.raises(GraphGenerationError) as excinfo:
        generate_graph_repository(_write(tmp_path, _with_lifecycle(lifecycle)), tmp_path / "out")
    assert str(excinfo.value).endswith(" (GE153). No ref was changed. 3 more problem(s) in graph.ref_lifecycle; "
                                       "'szzbench validate-graph' lists them.")


# --- GW151 reads the section too ------------------------------------------------------------

def _rewind(lifecycle) -> dict:
    """test_branch_rewinds' reproduction of issue #174: c2 resets main from c1 to f1, and no ref reaches c1."""
    def commit(cid, parents, path, branch="main"):
        return {"id": cid, "branch": branch, "parents": parents, "message": f"Change {cid}", "role": "intermediate",
                "operations": [{"type": "write_file", "path": path, "content": f"{cid}\n"}]}
    data = copy.deepcopy(SZZG_0072)
    data["commits"] = [commit("c0", [], "a.txt"), commit("c1", ["c0"], "b.txt"),
                       commit("f1", ["c0"], "f.txt", branch="feature"), commit("c2", ["f1"], "g.txt")]
    data["bugs"] = [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                     "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}]}]
    data["expected_szz"] = {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}
    data["graph"] = {"model": "commit_dag", "ref_lifecycle": lifecycle}
    return data


def _gw151(result: ValidationResult) -> list[str | None]:
    return [f.location for f in result.findings if f.code == "GW151"]


def test_gw151_and_these_errors_read_the_section_alike():
    """GW151 (issue #174) skips a section whose tags or delete_branches is not a list, "the generator refuses it";
    validation now says so itself.  A tag that keeps c1 silences GW151 whether or not its name is valid, and the
    name is an error of its own."""
    assert _gw151(validate_graph_static(_rewind({}))) == ["commits[3].parents"]
    assert _errors(validate_graph_static(_rewind({}))) == []
    for lifecycle, expected in [({"tags": 5}, [("GE155", "graph.ref_lifecycle.tags")]),
                                ({"delete_branches": "feature"}, [("GE153", "graph.ref_lifecycle.delete_branches")]),
                                ({"tags": [{"name": "keep", "commit": "c1"}]}, []),
                                ({"tags": [{"name": "keep c1", "commit": "c1"}]}, [("GE157", "graph.ref_lifecycle.tags[0].name")])]:
        result = validate_graph_static(_rewind(lifecycle))
        assert _errors(result) == expected, lifecycle
        assert _gw151(result) == [], lifecycle
