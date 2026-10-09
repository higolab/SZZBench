"""A rewritten repository is stale, and ``verify`` says how it differs from the generated one (issue #167).

``szzbench verify`` checked that every hash of ``commit-map.json`` named a
commit with the right subject, and the staleness check of #93 asked
``git cat-file`` whether each hash was there.  A dangling commit satisfied
both: after ``git reset --hard HEAD~2`` in a generated SZZ-0005, or
``git commit --amend`` of its fixing commit, ``git log --all`` no longer showed
the oracle, yet ``verify --strict`` reported no error and ``generate-all-repos``
skipped the output as up to date, so ``evaluate`` would have scored a tool
against commits it could not see.  An author or a date edited in the commit
map passed ``verify`` as well.

Now an output is stale unless every commit it was generated with is reachable
from a ref (the reflog does not count; a graph scenario's ``ref_lifecycle``
may leave commits unreachable on purpose), and ``verify`` answers whether the
repository is still as the generator left it: the commit map's author and
dates are the commits', each commit's parent is the previous one, every commit
is reachable, the default branch points at the last commit and is checked out,
and the index and the working tree are clean.  What an SZZ tool may do -- check
out, commit, branch, tag -- keeps the output fresh, and ``verify`` reports the
moved HEAD or branch.  The commit map's metadata is not part of the repository
id, so an edited author leaves the output fresh; ``verify`` reports it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from szzbench import manifest
from szzbench.bulk_generator import generate_all_repositories
from szzbench.evaluator import evaluate_predictions
from szzbench.generator import generate_repository
from szzbench.gitutils import parse_author, run_git
from szzbench.verifier import verify_generated_repo

from support import git

ROOT = Path(__file__).resolve().parents[1]
CLASSIC, GRAPH = "SZZ-0005", "SZZG-0072"      # SZZG-0072 deletes the branch of f1 and f2 on purpose


def _layout(root: Path) -> tuple[Path, Path, Path]:
    classic, graph, generated = root / "scenarios", root / "advanced-scenarios", root / "generated"
    for suite, sid, name in (("scenarios", CLASSIC, "scenario.yml"),
                             ("advanced-scenarios", GRAPH, "scenario.graph.yml")):
        target = root / suite / sid / name
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / suite / sid / name).read_bytes())
    return classic, graph, generated


def _generate_all(classic, graph, generated):
    result = generate_all_repositories(scenarios_root=classic, advanced_scenarios_root=graph, output_root=generated)
    return {item.scenario_id: (item.status, item.stale_reason) for item in result.items}


@pytest.fixture(scope="module")
def pristine(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("pristine")
    assert set(_generate_all(*_layout(root)).values()) == {("generated", None)}
    return root


class Output:
    """A copy of the pristine layout, with the paths a test needs."""

    def __init__(self, pristine: Path, tmp_path: Path) -> None:
        self.root = tmp_path / "copy"
        shutil.copytree(pristine, self.root, symlinks=True)
        self.classic, self.graph = self.root / "scenarios", self.root / "advanced-scenarios"
        self.generated = self.root / "generated"

    def scenario(self, sid: str = CLASSIC) -> Path:
        if sid.startswith("SZZG-"):
            return self.graph / sid / "scenario.graph.yml"
        return self.classic / sid / "scenario.yml"

    def output(self, sid: str = CLASSIC) -> Path:
        return self.generated / sid / "default"

    def repo(self, sid: str = CLASSIC) -> Path:
        return self.output(sid) / "repo"

    def commit_map_path(self) -> Path:
        return self.output() / "metadata/commit-map.json"

    def commit_map(self) -> dict:
        return json.loads(self.commit_map_path().read_text(encoding="utf-8"))

    def staleness(self, sid: str = CLASSIC) -> str | None:
        return manifest.staleness(self.output(sid), self.scenario(sid))

    def verify(self):
        return verify_generated_repo(self.repo(), self.scenario())

    def errors(self) -> list[str]:
        return sorted(f.code for f in self.verify().findings if f.severity.upper() == "ERROR")

    def generate_all(self):
        return _generate_all(self.classic, self.graph, self.generated)


@pytest.fixture
def out(pristine, tmp_path) -> Output:
    return Output(pristine, tmp_path)


def test_a_generated_repository_verifies_and_is_fresh(out):
    assert out.errors() == []
    assert out.staleness() is None
    assert out.staleness(GRAPH) is None          # f1 and f2 are unreachable, as the scenario says


# ---------------------------------------------------------------------------
# the oracle's commits are no longer reachable (the issue's reproduction)
# ---------------------------------------------------------------------------

def _reset_two_commits(repo: Path) -> None:
    run_git(repo, ["reset", "-q", "--hard", "HEAD~2"])


def _amend_the_fixing_commit(repo: Path) -> None:
    run_git(repo, ["commit", "-q", "--amend", "--no-edit"])     # a new committer date, a new hash


@pytest.mark.parametrize("rewrite, unreachable", [(_reset_two_commits, ["c1", "c2"]),
                                                  (_amend_the_fixing_commit, ["c2"])],
                         ids=["reset-hard", "amend"])
def test_an_oracle_no_ref_reaches_is_stale_and_fails_verification(out, rewrite, unreachable):
    rewrite(out.repo())
    assert git(out.repo(), "cat-file", "-t", out.commit_map()["c2"]["hash"]) == "commit"   # still there, dangling
    assert out.staleness() == (f"its repository no longer reaches {len(unreachable)} of the 3 commits it was "
                               f"generated with ({', '.join(unreachable)})")
    findings = out.verify().findings
    assert sorted(f.code for f in findings if f.severity.upper() == "ERROR") == ["E604"] * len(unreachable) + ["E607"]
    assert [f.location for f in findings if f.code == "E604"] == [f"commits.{cid}" for cid in unreachable]
    assert all("not reachable from any branch, tag or HEAD" in f.message for f in findings if f.code == "E604")
    status, reason = out.generate_all()[CLASSIC]
    assert status == "generated" and reason.startswith("its repository no longer reaches")
    assert out.staleness() is None and out.errors() == []


def test_evaluate_refuses_an_output_whose_oracle_is_unreachable(out):
    c1 = out.commit_map()["c1"]["hash"]
    _reset_two_commits(out.repo())
    predictions = out.root / "predictions.jsonl"
    predictions.write_text(json.dumps({"scenario_id": CLASSIC, "inducing_commit": c1}) + "\n", encoding="utf-8")
    report = evaluate_predictions(predictions, generated_root=out.generated, scenarios_root=out.classic,
                                  advanced_scenarios_root=out.graph, reference_format="hash")
    assert report.scenarios == []                  # it used to be scored: PASS, on a c1 `git log --all` does not show
    assert any(error.startswith(f"{CLASSIC}: the generated repository is stale: its repository no longer reaches 2")
               for error in report.errors)


def test_the_commits_a_graph_scenario_leaves_unreachable_are_not_asked_for(out):
    run_git(out.repo(GRAPH), ["reset", "-q", "--hard", "HEAD~1"])           # c3, the tip of main
    assert out.staleness(GRAPH) == "its repository no longer reaches 1 of the 5 commits it was generated with (c3)"


def test_the_reflog_does_not_keep_a_commit_reachable(out):
    # the reflog of HEAD and of main still name c1 and c2; git log --all does not show them
    _reset_two_commits(out.repo())
    assert out.commit_map()["c2"]["hash"] in git(out.repo(), "reflog", "--format=%H")
    assert out.staleness() is not None


def test_a_reparented_commit_fails_verification(out):
    # c2 committed again on top of c0, with its tree, message, author and dates: c1 drops out of the history
    entries = out.commit_map()
    c2 = entries["c2"]
    name, email = parse_author(c2["author"])
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_DATE": c2["author_date"],
           "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email, "GIT_COMMITTER_DATE": c2["committer_date"]}
    tree = git(out.repo(), "rev-parse", f"{c2['hash']}^{{tree}}")
    reparented = run_git(out.repo(), ["commit-tree", tree, "-p", entries["c0"]["hash"], "-m", c2["message"]],
                         env=env).stdout.strip()
    run_git(out.repo(), ["update-ref", "refs/heads/main", reparented])
    entries["c2"]["hash"] = reparented
    out.commit_map_path().write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    findings = out.verify().findings
    assert sorted(f.code for f in findings if f.severity.upper() == "ERROR") == ["E604", "E606"]
    parent = next(f for f in findings if f.code == "E606")
    assert parent.location == "commits.c2" and entries["c0"]["hash"] in parent.message
    assert entries["c1"]["hash"] in parent.message                                  # the parent it should have


# ---------------------------------------------------------------------------
# the commit map's author and dates
# ---------------------------------------------------------------------------

def _edit_c1(out: Output, **fields) -> None:
    entries = out.commit_map()
    entries["c1"].update(fields)
    out.commit_map_path().write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


@pytest.mark.parametrize("fields, field", [
    ({"author": "Mallory <mallory@example.com>"}, "author"),
    ({"author": "Aiko Mori <mallory@example.com>"}, "author"),
    ({"author_date": "1999-01-01T00:00:00Z"}, "author_date"),
    ({"committer_date": "1999-01-01T00:00:00Z"}, "committer_date"),
    ({"author_date": "not a date"}, "author_date"),
], ids=["author", "e-mail", "author-date", "committer-date", "not-a-date"])
def test_a_commit_map_that_records_other_metadata_fails_verification(out, fields, field):
    _edit_c1(out, **fields)
    findings = [f for f in out.verify().findings if f.severity.upper() == "ERROR"]
    assert [(f.code, f.location) for f in findings] == [("E605", "commits.c1")]
    assert f"records {field} {fields[field]!r} for 'c1'" in findings[0].message
    # the repository id digests the hashes only, so the output is still fresh
    assert out.staleness() is None


def test_the_issues_edit_of_the_commit_map_fails_verification(out):
    _edit_c1(out, author="Mallory <mallory@example.com>", role="bug_fixing", author_date="1999-01-01T00:00:00Z")
    assert out.errors() == ["E605", "E605"]                         # the author and the author date, not the role


def _in_tokyo(timestamp: str) -> str:
    """``timestamp`` (``...Z``) as the same instant at ``+09:00``."""
    instant = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return instant.astimezone(timezone(timedelta(hours=9))).isoformat()


def test_the_dates_are_compared_as_instants_and_role_and_date_not_at_all(out):
    recorded = out.commit_map()["c1"]
    assert recorded["author_date"].endswith("Z") and recorded["committer_date"].endswith("Z")
    _edit_c1(out, author_date=recorded["author_date"][:-1] + "+00:00",
             committer_date=_in_tokyo(recorded["committer_date"]),
             author=f"  {recorded['author'].replace(' <', '<')}  ", role="bug_fixing", date="1999-01-01T00:00:00Z")
    assert out.errors() == []


def test_an_author_whose_punctuation_git_drops_still_verifies(tmp_path):
    # Git 2.39 records "J. R. R. Tolkien Jr" for this author, Git 2.50 keeps the final period
    data = yaml.safe_load((ROOT / "scenarios" / CLASSIC / "scenario.yml").read_text(encoding="utf-8"))
    data["commits"][1]["author"] = "J. R. R. Tolkien Jr. <jrrt@example.com>"
    scenario = tmp_path / CLASSIC / "scenario.yml"
    scenario.parent.mkdir()
    scenario.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    commit_map, verified = generate_repository(scenario, tmp_path / "out", force=True)
    recorded = git(tmp_path / "out/repo", "log", "-1", "--format=%an", commit_map["c1"]["hash"])
    assert recorded in {"J. R. R. Tolkien Jr", "J. R. R. Tolkien Jr."}
    assert verified is not None and not verified.has_errors(), verified.to_dict()


# ---------------------------------------------------------------------------
# what an SZZ tool may do: fresh, but no longer the generated repository
# ---------------------------------------------------------------------------

def _tool_commits(repo: Path) -> None:
    run_git(repo, ["-c", "user.name=A tool", "-c", "user.email=tool@example.com",
                   "commit", "-q", "--allow-empty", "-m", "a commit of the tool's own"])


def _detached_with_a_commit_branch_and_tag(repo: Path) -> None:      # the existing test of #93
    run_git(repo, ["checkout", "-q", "--detach", "HEAD~1"])
    _tool_commits(repo)
    run_git(repo, ["branch", "tool-branch"])
    run_git(repo, ["tag", "tool-tag"])


def _on_another_branch(repo: Path) -> None:
    run_git(repo, ["checkout", "-q", "-b", "tool-branch", "HEAD~1"])


def _modified(repo: Path) -> None:
    path = repo / "src/main/java/example/UserRequest.java"
    path.write_text(path.read_text(encoding="utf-8") + "// a tool's note\n", encoding="utf-8")


def _untracked(repo: Path) -> None:
    (repo / "tool-output.txt").write_text("results\n", encoding="utf-8")


def _staged(repo: Path) -> None:
    _untracked(repo)
    run_git(repo, ["add", "tool-output.txt"])


@pytest.mark.parametrize("act, codes", [
    (_detached_with_a_commit_branch_and_tag, ["E608"]),
    (_on_another_branch, ["E608"]),
    (_tool_commits, ["E607"]),                                     # on main, above the last commit
    (_modified, ["E609"]),
    (_untracked, ["E609"]),
    (_staged, ["E609"]),
], ids=["detached-commit-branch-tag", "another-branch", "commit-on-main", "modified", "untracked", "staged"])
def test_what_an_szz_tool_may_do_keeps_the_output_fresh_but_fails_verification(out, act, codes):
    act(out.repo())
    assert out.staleness() is None
    assert out.generate_all()[CLASSIC] == ("skipped", None)
    assert out.errors() == codes


def test_verification_writes_nothing_into_the_repository(out):
    # a file whose stat data no longer matches the index: a plain `git status` rewrites the index
    path = out.repo() / "src/main/java/example/UserRequest.java"
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 5_000_000_000))
    git_dir = out.repo() / ".git"

    def snapshot():
        return {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in git_dir.rglob("*") if p.is_file()}

    before = snapshot()
    assert out.errors() == []
    assert snapshot() == before


# ---------------------------------------------------------------------------
# the CLI, with the relative paths it is usually given
# ---------------------------------------------------------------------------

def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "src")})


def test_the_cli_reports_an_unreachable_oracle_under_relative_paths(out):
    verify = ["verify", f"generated/{CLASSIC}/default/repo", "--scenario", f"scenarios/{CLASSIC}/scenario.yml",
              "--strict"]
    generate = ["generate-all-repos", "--out-root", "generated", "--scenarios-root", "scenarios",
                "--advanced-scenarios-root", "advanced-scenarios"]
    assert _cli(out.root, *verify).returncode == 0
    _reset_two_commits(out.repo())
    verified = _cli(out.root, *verify)
    assert verified.returncode == 1 and "[ERROR] E604: Logical commit 'c1'" in verified.stdout
    regenerated = _cli(out.root, *generate)
    assert regenerated.returncode == 0, regenerated.stderr
    assert f"Regenerated [classic] {CLASSIC}" in regenerated.stdout
    assert "its repository no longer reaches 2 of the 3 commits it was generated with (c1, c2)" in regenerated.stdout
    assert _cli(out.root, *verify).returncode == 0
