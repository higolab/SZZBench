"""The test suite keeps the conventions of tests/README.md (issue #107).

The first version of the audit looked for direct Git calls line by line and
missed one whose argument list started on the next line (PR #108 review): it
ran Git with the caller's environment, so an ambient ``GIT_DIR`` broke the
test. This check reads the syntax tree instead.  It has no exception: even
``test_git_isolation.py``, which runs SZZBench under hostile Git environments,
sets up and reads its own repositories in the isolated one.
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent


def _direct_git_calls(path: Path) -> list[int]:
    """Lines where ``path`` starts ``git`` itself, without the isolated environment."""
    lines = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], (ast.List, ast.Tuple))):
            continue
        argv = node.args[0].elts
        if not (argv and isinstance(argv[0], ast.Constant) and argv[0].value == "git"):
            continue
        env = next((k.value for k in node.keywords if k.arg == "env"), None)
        isolated = isinstance(env, ast.Call) and isinstance(env.func, ast.Name) and env.func.id == "git_env"
        if not isolated:
            lines.append(node.lineno)
    return lines


def test_the_tests_run_git_only_in_the_isolated_environment():
    offenders = [f"{path.name}:{line}" for path in sorted(TESTS.glob("*.py"))
                 if path.name != "support.py" for line in _direct_git_calls(path)]
    assert offenders == [], "run Git through tests/support.py (git, git_stdout, git_bytes, git_env)"


def test_the_check_sees_a_call_split_over_lines(tmp_path):
    sample = tmp_path / "sample.py"
    sample.write_text('import subprocess\nsubprocess.run(\n    ["git", "show", "HEAD:x"],\n    check=True,\n)\n'
                      'subprocess.run(["git", "status"], env=git_env())\n', encoding="utf-8")
    assert _direct_git_calls(sample) == [2]
