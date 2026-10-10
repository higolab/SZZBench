"""The numbers the Quickstart promises are the numbers of the recorded run (issue #189).

The Quickstart of `README.md` says that re-scoring
`examples/pydriller-run/predictions.jsonl` prints `PASS: 161`, `FAIL: 118`,
precision 0.781 and recall 0.689, and that the tool passes 68.7 % of the
`control` scenarios and 2.2 % of the `discriminating` ones.  Both halves of
`README.md`, the example's README, the comparison tables of the other example
runs and `docs/baselines.md` quote that run, and nothing compared any of them
with the report it came from, `examples/pydriller-run/evaluation-results.md`.
These tests take the numbers from the report (the tier shares from its rows and
each scenario's `meta.tier`) and check every copy against them; the last one
re-scores the predictions when the generated repositories are there.
"""
from __future__ import annotations

import functools
import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

from szzbench.evaluator import evaluate_predictions

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "pydriller-run"
RECORDED = EXAMPLE / "evaluation-results.md"
GENERATED = REPO / "generated-input-repos"

#: The summary lines of the report that the copies quote, by field.
SUMMARY_FIELDS = {
    "Total scenarios": "total", "PASS": "pass", "FAIL": "fail", "True positives": "tp",
    "False positives": "fp", "Hard false positives": "hard_fp", "False negatives": "fn",
    "Precision": "precision", "Recall": "recall",
}


def _pattern(template: str) -> str:
    """``#`` is a quoted number, and a space matches any run of whitespace, so
    re-wrapping a paragraph does not lose the copy."""
    return template.replace(" ", r"\s+").replace("#", r"(\d+(?:\.\d+)?)")


_ROW = r"\| \*PyDriller 2\.12\*[^|]*\| # \| # / # \| # / # \| # \| # \| # \| # \| # \|"
_ROW_FIELDS = ("pass", "control_pass", "control_total", "discriminating_pass", "discriminating_total",
               "tp", "fp", "fn", "precision", "recall")

#: Each copy: its file, the section of it to read (None: all of it), and what
#: it quotes -- a pattern, and the fields its numbers are, in order.
COPIES = {
    "README.md (English Quickstart)": ("README.md", "## Quickstart", [
        (r"writes # repositories", ("total",)),
        (r"`PASS: #`, `FAIL: #`", ("pass", "fail")),
        (r"precision # and recall #", ("precision", "recall")),
        (r"# % of the `control`", ("control_share",)),
        (r"# % of the `discriminating`", ("discriminating_share",)),
    ]),
    "README.md (Japanese Quickstart)": ("README.md", "## クイックスタート", [
        (r"# 個のリポジトリ", ("total",)),
        (r"`PASS: #`、`FAIL: #`", ("pass", "fail")),
        (r"precision #、recall #", ("precision", "recall")),
        (r"`control` の # %", ("control_share",)),
        (r"`discriminating` の # %", ("discriminating_share",)),
    ]),
    "examples/pydriller-run/README.md": ("examples/pydriller-run/README.md", None, [
        (r"\| scenarios \| # \|", ("total",)),
        (r"\| PASS / FAIL \| \*\*# / #\*\* \|", ("pass", "fail")),
        (r"\| true positives \| # \|", ("tp",)),
        (r"\| false positives \| # \(# of them \*hard\*\) \|", ("fp", "hard_fp")),
        (r"\| false negatives \| # \|", ("fn",)),
        (r"\| precision / recall \| \*\*# / #\*\* \|", ("precision", "recall")),
        (r"\| `control` \| # / # \| # % \|", ("control_pass", "control_total", "control_share")),
        (r"\| `discriminating` \| \*\*# / #\*\* \| \*\*# %\*\* \|",
         ("discriminating_pass", "discriminating_total", "discriminating_share")),
        (r"\| PyDriller 2\.12 \| # \|", ("pass",)),
    ]),
    "examples/pyszz-run/README.md": ("examples/pyszz-run/README.md", None, [(_ROW, _ROW_FIELDS)]),
    "examples/szz-unleashed-run/README.md": ("examples/szz-unleashed-run/README.md", None, [(_ROW, _ROW_FIELDS)]),
    "examples/token-bszz-run/README.md": ("examples/token-bszz-run/README.md", None, [(_ROW, _ROW_FIELDS)]),
    "docs/baselines.md": ("docs/baselines.md", None, [
        (r"PyDriller 2\.12 passes # of the # scenarios and # of the # `discriminating` ones",
         ("pass", "total", "discriminating_pass", "discriminating_total")),
        (r"of PyDriller's # are", ("pass",)),
    ]),
}


def _summary(text: str) -> dict[str, str]:
    values = {}
    for line in text.split("\n## Information")[0].splitlines():
        match = re.match(r"- ([^:]+): (\S+)$", line)
        if match and match.group(1) in SUMMARY_FIELDS:
            values[SUMMARY_FIELDS[match.group(1)]] = match.group(2)
    return values


def _statuses(text: str) -> dict[str, str]:
    """Scenario id to status, from the rows of the report's results table."""
    rows = [line.split("|")[1:-1] for line in text.splitlines() if line.startswith("| SZZ")]
    return {cells[0].strip(): cells[1].strip() for cells in rows}


@functools.lru_cache(maxsize=None)
def _tiers() -> dict[str, str | None]:
    files = sorted(REPO.glob("scenarios/*/scenario.yml")) + sorted(REPO.glob("advanced-scenarios/*/scenario.graph.yml"))
    return {path.parent.name: (yaml.safe_load(path.read_text(encoding="utf-8")).get("meta") or {}).get("tier")
            for path in files}


def _recorded() -> dict[str, str]:
    """What the report says, in the fields the copies quote."""
    text = RECORDED.read_text(encoding="utf-8")
    values = _summary(text)
    tiers = _tiers()
    statuses = _statuses(text)
    for tier in ("control", "discriminating"):
        ids = [sid for sid in statuses if tiers.get(sid) == tier]
        passed = sum(statuses[sid] == "PASS" for sid in ids)
        values[f"{tier}_pass"], values[f"{tier}_total"] = str(passed), str(len(ids))
        values[f"{tier}_share"] = f"{100 * passed / len(ids):.1f}"
    return values


def _section(text: str, heading: str | None) -> str | None:
    """The section under ``heading`` up to the next ``##``; None when there is none."""
    if heading is None:
        return text
    start = text.find(f"\n{heading}\n")
    if start == -1:
        return None
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else len(text)]


def test_the_report_scores_the_shipped_suite():
    # The Quickstart re-scores with --include-generated, so every shipped
    # scenario counts: one the report lacks, or one it has and the suite
    # retired, would make the printed counts differ from the quoted ones.
    text = RECORDED.read_text(encoding="utf-8")
    statuses = _statuses(text)
    shipped = set(_tiers())
    assert set(statuses) == shipped, (
        f"rows for retired scenarios: {sorted(set(statuses) - shipped)}; "
        f"shipped scenarios without a row: {sorted(shipped - set(statuses))}; re-run the example")
    summary = _summary(text)
    counts = Counter(statuses.values())
    assert (str(len(statuses)), str(counts["PASS"]), str(counts["FAIL"])) == \
        (summary["total"], summary["pass"], summary["fail"])


def test_every_copy_quotes_the_recorded_report():
    recorded = _recorded()
    problems = []
    for name, (path, heading, patterns) in COPIES.items():
        text = _section((REPO / path).read_text(encoding="utf-8"), heading)
        if text is None:
            problems.append(f"{name}: {path} has no section `{heading}`")
            continue
        for pattern, fields in patterns:
            matches = re.findall(_pattern(pattern), text)
            if not matches:
                problems.append(f"{name}: no longer quotes {', '.join(fields)} (pattern {pattern!r})")
            for match in matches:
                quoted = (match,) if isinstance(match, str) else match
                for field, value in zip(fields, quoted):
                    if value != recorded[field]:
                        problems.append(f"{name}: {field} is {value}, the report says {recorded[field]}")
    assert problems == [], "copies that disagree with examples/pydriller-run/evaluation-results.md:\n" + \
        "\n".join(problems)


def test_rescoring_the_example_reproduces_the_report():
    # CI has no generated repositories; a checkout that ran generate-all-repos does.
    if not GENERATED.is_dir():
        pytest.skip("needs generated-input-repos/ (szzbench generate-all-repos)")
    report = evaluate_predictions(
        EXAMPLE / "predictions.jsonl", generated_root=GENERATED, scenarios_root=REPO / "scenarios",
        advanced_scenarios_root=REPO / "advanced-scenarios", include_generated=True)
    stale = [error for error in report.errors if "the generated repository is stale" in error]
    if stale:
        pytest.skip(f"{len(stale)} generated output(s) are stale; szzbench generate-all-repos regenerates them")
    assert report.to_markdown().splitlines() == RECORDED.read_text(encoding="utf-8").splitlines()
