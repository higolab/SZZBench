"""What ``evaluate``, ``baselines`` and ``coverage`` do with inputs they cannot use.

``evaluate`` exited 0, ``--fail-on-non-pass`` included, when it scored no
scenario: an empty predictions file, or ``--include-generated`` over a root
without outputs or one that does not exist (issue #141).  ``baselines`` and
``coverage`` already refused such a run.

The three commands created the ``--out`` directory only after their work, so
an ``--out`` naming a file ended them in a FileExistsError traceback, after a
whole ``baselines`` run (issue #143).  It is now checked, and created, first.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from szzbench import cli
from szzbench.cli import main

ROOT = Path(__file__).resolve().parents[1]
SUITES = ["--scenarios-root", str(ROOT / "scenarios"), "--advanced-scenarios-root", str(ROOT / "advanced-scenarios")]


@pytest.mark.parametrize("case", ["empty file", "blank lines", "root without outputs", "root that does not exist"])
def test_an_evaluation_that_scores_nothing_fails_and_names_the_input(tmp_path, capsys, case):
    predictions, root = tmp_path / "predictions.jsonl", tmp_path / "generated"
    if case in ("empty file", "blank lines"):
        predictions.write_text("" if case == "empty file" else "\n  \n\n", encoding="utf-8")
        args = ["--predictions", str(predictions), "--generated-root", str(root)]
        message = f"EVALUATE_FAILED: no scenario was scored: {predictions} holds no prediction record."
    elif case == "root without outputs":
        root.mkdir()
        args = ["--include-generated", "--generated-root", str(root)]
        message = f"EVALUATE_FAILED: no scenario was scored: --generated-root {root} holds no <scenario-id>/default output"
    else:
        args = ["--include-generated", "--generated-root", str(root)]
        message = f"EVALUATE_FAILED: --generated-root {root} does not exist;"
    for flags in ([], ["--fail-on-non-pass"]):
        assert main(["evaluate", *args, *SUITES, "--out", str(tmp_path / "out"), *flags]) == 1
        assert f"[ERROR] {message}" in capsys.readouterr().err
    report = tmp_path / "out/evaluation-results.json"
    if case == "root that does not exist":
        assert not report.exists()                                  # refused before anything ran
    else:                                                           # the --out report says so too
        assert json.loads(report.read_text(encoding="utf-8"))["errors"][-1].startswith(message)


@pytest.mark.parametrize("command, work", [("evaluate", "evaluate_predictions"), ("baselines", "run_baselines"),
                                           ("coverage", "run_coverage")])
def test_an_out_that_cannot_be_a_directory_is_refused_before_the_work(tmp_path, capsys, monkeypatch, command, work):
    def work_before_out(*args, **kwargs):
        raise AssertionError(f"{command} did its work before it checked --out")

    monkeypatch.setattr(cli, work, work_before_out)
    results = tmp_path / "results"
    results.write_text("", encoding="utf-8")                      # a file where the command expects a directory
    extra = ["--predictions", str(tmp_path / "predictions.jsonl")] if command == "evaluate" else []
    code = f"{command.upper()}_FAILED"
    for out, message in [(results, f"[ERROR] {code}: --out must be a directory, and {results} is not one."),
                         (results / "sub", f"[ERROR] {code}: cannot create the --out directory {results / 'sub'} (")]:
        assert main([command, *extra, "--generated-root", str(tmp_path), *SUITES, "--out", str(out)]) == 1
        stderr = capsys.readouterr().err.splitlines()
        assert len(stderr) == 1 and stderr[0].startswith(message), stderr
