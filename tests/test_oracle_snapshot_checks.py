"""W301/W320/W330 and the deletion-fix declaration (`fix.removed_statement`).

These three warnings report facts that a handful of scenarios exist to exhibit:
a deliberately duplicated fault statement, a fault line reformatted between BIC
and BFC, a fix whose text already occurs in another overload.  Until the triage
of the remaining 18 warnings they had no declaration mechanism at all, so the
only way to a clean run was to suppress them or to change the scenario into
something it was not meant to be.  They now honour `meta.factors`, the same way
W430/W431 already did.
"""
from __future__ import annotations


from szzbench.validator import simulate_commits, validate_oracle_against_snapshots

JAVA = "src/main/java/example/Range.java"


def check(data: dict) -> list[str]:
    snapshots, sim = simulate_commits(data)
    assert not sim.has_errors(), [f.code for f in sim.findings]
    return [f.code for f in validate_oracle_against_snapshots(data, snapshots).findings]


def scenario(*, factors: list[str], commits: list[dict], fault: dict, fix: dict) -> dict:
    return {
        "schema_version": "1.0",
        "meta": {"id": "SZZ-9901", "title": "Fixture", "category": "fixture",
                 "tier": "control", "factors": factors},
        "repository": {"name": "fixture", "default_branch": "main", "language": "java"},
        "commits": commits,
        "bugs": [{"id": "B001", "bug_fixing_commit": commits[-1]["id"],
                  "bug_introducing_commits": ["c1"], "fault": fault, "fix": fix}],
    }


def write(cid: str, body: str, role: str = "initial") -> dict:
    return {"id": cid, "message": f"commit {cid}", "role": role,
            "operations": [{"type": "write_file", "path": JAVA, "content": body}]}


# --- W301: the fault statement occurs more than once -------------------------

DUPLICATED = "package example;\npublic class Range {\n  boolean a() { return x > min; }\n  boolean b() { return x > min; }\n}\n"


def test_w301_honours_a_declared_duplication():
    data = scenario(
        factors=["single-bic"],
        commits=[write("c0", "package example;\npublic class Range {\n}\n"),
                 write("c1", DUPLICATED, "bug_introducing"),
                 write("c2", DUPLICATED.replace("x > min", "x >= min"), "bug_fixing")],
        fault={"commit": "c1", "file": JAVA, "statement": "return x > min;", "change_type": "line_modification"},
        fix={"commit": "c2", "file": JAVA, "statement": "return x >= min;", "fix_type": "line_modification"},
    )
    assert "W301" in check(data)

    data["meta"]["factors"] = ["single-bic", "duplicate-statement"]
    assert "W301" not in check(data)


# --- W320: the fault line is rewritten between BIC and BFC -------------------

def _rewrite_scenario(factors: list[str]) -> dict:
    one_line = "package example;\npublic class Range {\n  boolean a() { return x > min; }\n}\n"
    reformatted = "package example;\npublic class Range {\n  boolean a() {\n    return x > min;\n  }\n}\n"
    fixed = reformatted.replace("x > min", "x >= min")
    data = scenario(
        factors=factors,
        commits=[write("c0", "package example;\npublic class Range {\n}\n"),
                 write("c1", one_line, "bug_introducing"),
                 write("c2", reformatted, "intermediate"),
                 write("c3", fixed, "bug_fixing")],
        fault={"commit": "c1", "file": JAVA, "statement": "boolean a() { return x > min; }",
               "change_type": "line_modification"},
        fix={"commit": "c3", "file": JAVA, "statement": "return x >= min;", "fix_type": "line_modification"},
    )
    return data


def test_w320_honours_a_declared_rewrite():
    assert "W320" in check(_rewrite_scenario(["single-bic"]))
    assert "W320" not in check(_rewrite_scenario(["single-bic", "formatting-after-bic"]))


# --- W330 and the deletion fix ----------------------------------------------

GUARDED = "package example;\npublic class Range {\n  boolean a() {\n    if (x == 0) {\n      return false;\n    }\n    return x >= 0;\n  }\n}\n"
PLAIN = "package example;\npublic class Range {\n  boolean a() {\n    return x >= 0;\n  }\n}\n"


def _deletion_scenario(fix: dict, factors=("single-bic",)) -> dict:
    return scenario(
        factors=list(factors),
        commits=[write("c0", PLAIN),
                 write("c1", GUARDED, "bug_introducing"),
                 write("c2", PLAIN, "bug_fixing")],
        fault={"commit": "c1", "file": JAVA, "statement": "return false;", "change_type": "line_addition"},
        fix=fix,
    )


def test_w330_fires_when_the_fix_text_predates_the_fix():
    """Naming a surviving line as the fix of a deletion is what W330 is for."""
    data = _deletion_scenario({"commit": "c2", "file": JAVA, "statement": "return x >= 0;",
                               "fix_type": "line_modification"})
    assert "W330" in check(data)


def test_a_deletion_fix_is_declared_by_what_it_removed():
    data = _deletion_scenario({"commit": "c2", "file": JAVA,
                               "removed_statement": "if (x == 0) {", "fix_type": "line_deletion"})
    assert check(data) == []


def test_e312_when_the_removed_statement_is_still_there():
    data = _deletion_scenario({"commit": "c2", "file": JAVA,
                               "removed_statement": "return x >= 0;", "fix_type": "line_deletion"})
    assert "E312" in check(data)


def test_e311_still_requires_one_of_the_three_statement_keys():
    data = _deletion_scenario({"commit": "c2", "file": JAVA, "fix_type": "line_deletion"})
    assert "E311" in check(data)


def test_e313_when_the_removed_statement_never_existed():
    """Checking only that the text is gone afterwards accepts a false oracle.

    A statement that occurs in no snapshot is trivially absent at the fix commit,
    so `removed_statement: this_never_existed();` passed both validation and
    verification until E313 required it to have been there beforehand.
    """
    data = _deletion_scenario({"commit": "c2", "file": JAVA,
                               "removed_statement": "this_statement_never_existed();",
                               "fix_type": "line_deletion"})
    assert "E313" in check(data)


def test_the_declarations_reach_the_git_backed_verifier(tmp_path):
    """A scenario clean under `validate --lint` must be clean under `verify --strict`.

    W301 lived in the verifier as well, where the declaration did not apply, so
    SZZ-0111/0133/0146 validated cleanly and then failed verification.
    """
    from szzbench.generator import generate_repository
    from szzbench.verifier import verify_generated_repo
    import yaml

    data = scenario(
        factors=["single-bic", "duplicate-statement"],
        commits=[write("c0", "package example;\npublic class Range {\n}\n"),
                 write("c1", DUPLICATED, "bug_introducing"),
                 write("c2", DUPLICATED.replace("x > min", "x >= min"), "bug_fixing")],
        fault={"commit": "c1", "file": JAVA, "statement": "return x > min;", "change_type": "line_modification"},
        fix={"commit": "c2", "file": JAVA, "statement": "return x >= min;", "fix_type": "line_modification"},
    )
    path = tmp_path / "scenario.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    out = tmp_path / "out"
    generate_repository(path, out, force=True)

    declared = verify_generated_repo(out / "repo", path)
    assert [f.code for f in declared.findings if f.code == "W301"] == []

    data["meta"]["factors"] = ["single-bic"]
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    undeclared = verify_generated_repo(out / "repo", path)
    assert [f.code for f in undeclared.findings if f.code == "W301"] != []
