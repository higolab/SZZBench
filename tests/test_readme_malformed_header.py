"""A README header edited out of its exact shape (issue #184).

`szzbench readme` recognised a header only in its exact shape.  Anything else
-- an extra blank line, a missing end marker, prose above the title -- was
"has no generated header", `--write` put a fresh header above the old one, and
from then on the doubled README passed `szzbench readme`, W455/GW455 and the
shipped-README test.  These tests pin the repair: such a header is reported as
malformed and replaced whole, a second header in the body is stale, a BOM and
CRLF endings are no difference and survive a write, `--write` checks what it
wrote, and a README that is not UTF-8 is listed as unreadable.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from szzbench import readme as readme_module
from szzbench.cli import main
from szzbench.readme import (
    HEADER_BEGIN,
    HEADER_END,
    apply_header,
    check_readme,
    render_header,
    scenario_files,
    suite_of,
)
from szzbench.scenario import load_yaml

REPO = Path(__file__).resolve().parents[1]
CLASSIC = REPO / "scenarios/SZZ-0005/scenario.yml"
GRAPH = REPO / "advanced-scenarios/SZZG-0001/scenario.graph.yml"


def _shipped(scenario: Path) -> tuple[str, str, str]:
    """``(text, header, body)`` of a shipped README: the file, its header, and what follows it."""
    data, _ = load_yaml(scenario)
    header = render_header(data, suite_of(scenario))
    text = scenario.with_name("README.md").read_text(encoding="utf-8")
    assert text.startswith(header) and text[len(header):].startswith("\n## Purpose")
    return text, header, text[len(header):]


TEXT, HEADER, BODY = _shipped(CLASSIC)
TITLE = HEADER.split("\n", 1)[0] + "\n"


def _begins(text: str) -> int:
    return text.count("<!-- szzbench:header")


def _ends(text: str) -> int:
    return text.count(HEADER_END)


# --- the Issue's table: each input differs from the current file in one way ----------------

MALFORMED = {
    "two-blank-lines": (TEXT.replace(TITLE + "\n", TITLE + "\n\n", 1),
                        "2 blank lines between the title line and the begin marker, not one"),
    "no-blank-line": (TEXT.replace(TITLE + "\n", TITLE, 1),
                      "no blank line between the title line and the begin marker"),
    "no-end-marker": (TEXT.replace(HEADER_END + "\n", "", 1), "no end marker after the table"),
    "end-marker-misspelled": (TEXT.replace(HEADER_END, "<!-- /SZZBench:header -->", 1),
                              "the end marker reads '<!-- /SZZBench:header -->', not '<!-- /szzbench:header -->'"),
    "begin-marker-trailing-space": (TEXT.replace(HEADER_BEGIN, HEADER_BEGIN + " ", 1),
                                    "the begin marker has trailing whitespace"),
    "blank-line-in-table": (TEXT.replace("| tier |", "\n| tier |", 1), "a blank line inside the table"),
}


@pytest.mark.parametrize("name", MALFORMED)
def test_a_malformed_header_is_named_and_replaced_whole(name):
    text, reason = MALFORMED[name]
    assert check_readme(text, HEADER) == [f"header is malformed: {reason}"]
    written = apply_header(text, HEADER)
    assert written == HEADER + BODY, "exactly one header, and the body after the old one byte for byte"
    assert (_begins(written), _ends(written)) == (1, 1)
    assert check_readme(written, HEADER) == []


def test_text_before_the_title_is_kept_under_the_new_header():
    text = "Some intro line.\n\n" + TEXT
    assert check_readme(text, HEADER) == ["header is malformed: text before the title line"]
    written = apply_header(text, HEADER)
    assert written == HEADER + "\nSome intro line.\n" + BODY
    assert _begins(written) == 1 and check_readme(written, HEADER) == []


@pytest.mark.parametrize("separator", ["", "\n"], ids=["adjacent", "blank-line-between"])
def test_a_header_twice_is_stale_and_written_once(separator):
    text = HEADER + separator + HEADER + BODY
    second = HEADER.count("\n") + separator.count("\n") + 3            # the second begin marker's line
    assert check_readme(text, HEADER) == [f"carries a second header at line {second}, a leftover of an old header"]
    written = apply_header(text, HEADER)
    assert written == HEADER + BODY
    assert check_readme(written, HEADER) == []


def test_a_readme_the_old_write_doubled_is_repaired():
    # what `--write` on main made of "Some intro line." above the header: a new header
    # over the intro, the old title and the old header
    doubled = HEADER + "\nSome intro line.\n\n" + TEXT
    assert check_readme(doubled, HEADER) == [
        f"carries a second header at line {HEADER.count(chr(10)) + 6}, a leftover of an old header"]
    assert apply_header(doubled, HEADER) == HEADER + "\nSome intro line.\n" + BODY


def test_a_leftover_further_down_the_body_is_removed_with_the_prose_around_it_kept():
    text = HEADER + "\n## Purpose\n\nText.\n\n" + HEADER + "\n## Notes\n\nMore.\n" + HEADER_END + "\nLast.\n"
    problems = check_readme(text, HEADER)
    assert [p.split(" at line ")[0] for p in problems] == ["carries a second header", "carries a stray header end marker"]
    written = apply_header(text, HEADER)
    assert written == HEADER + "\n## Purpose\n\nText.\n\n## Notes\n\nMore.\nLast.\n"
    assert check_readme(written, HEADER) == []


def test_a_header_quoted_in_fenced_code_is_text():
    quoted = HEADER + "\n## Notes\n\n```markdown\n" + HEADER + "```\n"
    assert check_readme(quoted, HEADER) == []
    only_quoted = TITLE + "\n## Notes\n\n```markdown\n" + HEADER + "```\n"
    assert check_readme(only_quoted, HEADER) == ["has no generated header"]
    written = apply_header(only_quoted, HEADER)
    assert written == HEADER + "\n## Notes\n\n```markdown\n" + HEADER + "```\n"
    assert check_readme(written, HEADER) == []


INDENTED_EXAMPLE = ("\n## Notes\n\nA custom header looks like this:\n\n"
                    "    <!-- szzbench:header v1 -->\n    | custom | example |\n    <!-- /szzbench:header -->\n\n"
                    "The example ends here.\n")


@pytest.mark.parametrize("indent", ["    ", "\t", "     "], ids=["four-spaces", "tab", "five-spaces"])
def test_a_header_quoted_in_indented_code_is_text(tmp_path, capsys, indent):
    """Four-space-indented code quoted a marker as text too; it was a second header and --write
    deleted its comment lines (PR #222 review)."""
    example = INDENTED_EXAMPLE.replace("    ", indent)
    current = TEXT + example
    assert check_readme(current, HEADER) == []
    assert apply_header(current, HEADER) == current
    malformed = MALFORMED["no-end-marker"][0] + example
    assert check_readme(malformed, HEADER) == ["header is malformed: no end marker after the table"]
    assert apply_header(malformed, HEADER) == current
    directory = _copy(tmp_path, CLASSIC, current)
    assert main(["readme", "--write", str(directory)]) == 0
    assert (directory / "README.md").read_bytes() == current.encode("utf-8")
    assert "1 README header(s) current, 0 rewritten" in capsys.readouterr().out


def test_a_marker_indented_by_up_to_three_spaces_is_still_a_marker():
    """Markdown reads such a line as an HTML block, so a header leftover indented so is still one."""
    leftover = TEXT + "\n   " + HEADER_BEGIN + "\n| tier | control |\n" + HEADER_END + "\n"
    assert any(problem.startswith("carries a second header") for problem in check_readme(leftover, HEADER))
    assert apply_header(leftover, HEADER) == TEXT


# --- a BOM and CRLF line endings ---------------------------------------------------------

def _crlf(text: str) -> str:
    return text.replace("\n", "\r\n")


@pytest.mark.parametrize("variant", ["bom", "crlf", "bom-crlf"])
def test_a_bom_or_crlf_endings_alone_are_current(variant):
    text = ("﻿" if "bom" in variant else "") + (_crlf(TEXT) if "crlf" in variant else TEXT)
    assert check_readme(text, HEADER) == []


def test_a_write_keeps_the_bom_and_the_crlf_endings():
    data, _ = load_yaml(CLASSIC)
    data["meta"]["tier"] = "discriminating"
    fresh = render_header(data, "scenarios")
    text = "﻿" + _crlf(TEXT)
    assert check_readme(text, fresh) == ["header is stale: '| tier | `control` |' should read '| tier | `discriminating` |'"]
    written = apply_header(text, fresh)
    assert written == "﻿" + _crlf(fresh) + _crlf(BODY)
    assert check_readme(written, fresh) == []


def test_a_malformed_crlf_header_is_replaced_in_crlf():
    text = _crlf(MALFORMED["two-blank-lines"][0])
    assert check_readme(text, HEADER) == ["header is malformed: " + MALFORMED["two-blank-lines"][1]]
    written = apply_header(text, HEADER)
    assert written == _crlf(HEADER + BODY)
    assert "\n" not in written.replace("\r\n", ""), "no LF line mixed into a CRLF file"


def test_a_first_write_on_a_crlf_file_with_a_bom():
    text = "﻿" + _crlf(TITLE + "\n## Purpose\n\nProse.\n")
    assert check_readme(text, HEADER) == ["has no generated header"]
    assert apply_header(text, HEADER) == "﻿" + _crlf(HEADER + "\n## Purpose\n\nProse.\n")


# --- the command ------------------------------------------------------------------------------

def _copy(tmp_path: Path, scenario: Path, readme: str | bytes | None = None) -> Path:
    directory = tmp_path / scenario.parent.name
    shutil.copytree(scenario.parent, directory)
    path = directory / "README.md"
    if isinstance(readme, str):
        path.write_bytes(readme.encode("utf-8"))
    elif isinstance(readme, bytes):
        path.write_bytes(readme)
    return directory


@pytest.mark.parametrize("name", MALFORMED)
def test_the_command_reports_writes_once_and_is_then_current(tmp_path, capsys, name):
    text, reason = MALFORMED[name]
    directory = _copy(tmp_path, CLASSIC, text)
    assert main(["readme", str(directory)]) == 1
    assert f"header is malformed: {reason}" in capsys.readouterr().out
    assert main(["readme", "--write", str(directory)]) == 0
    written = (directory / "README.md").read_text(encoding="utf-8")
    assert written == HEADER + BODY and _begins(written) == 1
    capsys.readouterr()
    assert main(["readme", str(directory)]) == 0
    assert "1 README header(s) current" in capsys.readouterr().out


@pytest.mark.parametrize("prefix,convert", [("﻿", lambda t: t), ("", _crlf), ("﻿", _crlf)],
                         ids=["bom", "crlf", "bom-crlf"])
def test_the_command_leaves_a_current_bom_or_crlf_file_alone(tmp_path, prefix, convert):
    stored = (prefix + convert(TEXT)).encode("utf-8")
    directory = _copy(tmp_path, CLASSIC, stored)
    assert main(["readme", str(directory)]) == 0
    assert main(["readme", "--write", str(directory)]) == 0
    assert (directory / "README.md").read_bytes() == stored


def test_the_command_rewrites_a_stale_crlf_file_in_crlf(tmp_path):
    directory = _copy(tmp_path, CLASSIC, "﻿" + _crlf(TEXT.replace("| tier | `control` |", "| tier | `old` |")))
    assert main(["readme", "--write", str(directory)]) == 0
    assert (directory / "README.md").read_bytes() == ("﻿" + _crlf(TEXT)).encode("utf-8")


def test_a_title_with_a_line_break_is_written_on_one_line(tmp_path, capsys):
    data, _ = load_yaml(CLASSIC)
    data["meta"]["title"] = "Java annotation\nsyntax   change"
    assert render_header(data, "scenarios").startswith("# SZZ-0005: Java annotation syntax change\n\n" + HEADER_BEGIN)
    directory = _copy(tmp_path, CLASSIC, TITLE + "\n## Purpose\n\nProse.\n")
    (directory / "scenario.yml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert main(["readme", "--write", str(directory)]) == 0
    assert main(["readme", str(directory)]) == 0
    assert (directory / "README.md").read_text(encoding="utf-8") == HEADER + "\n## Purpose\n\nProse.\n"


def test_write_exits_1_when_the_file_it_wrote_is_still_stale(tmp_path, capsys, monkeypatch):
    directory = _copy(tmp_path, CLASSIC, MALFORMED["no-end-marker"][0])
    monkeypatch.setattr(readme_module, "apply_header", lambda text, header: text)     # a write that fixes nothing
    assert main(["readme", "--write", str(directory)]) == 1
    out = capsys.readouterr().out
    assert "rewrote: " in out and "    still stale after the write:\n        header is malformed: " in out
    assert out.rstrip().endswith("; 1 still stale")


def test_write_leaves_a_readme_alone_when_the_rendered_header_would_not_be_found_again(tmp_path, capsys):
    data, _ = load_yaml(CLASSIC)
    data["meta"]["category"] = "Basic semantic\nline changes"
    stored = MALFORMED["two-blank-lines"][0].encode("utf-8")
    directory = _copy(tmp_path, CLASSIC, stored)
    (directory / "scenario.yml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert main(["readme", "--write", str(directory)]) == 1
    assert "    not written:\n        the header rendered from the scenario file is not one title line" in \
        capsys.readouterr().out
    assert (directory / "README.md").read_bytes() == stored


@pytest.mark.parametrize("write", [False, True], ids=["check", "write"])
def test_a_readme_that_is_not_utf8_is_unreadable_not_a_traceback(tmp_path, capsys, write):
    stored = b"# SZZ-0005: caf\xe9\n"
    directory = _copy(tmp_path, CLASSIC, stored)
    assert main(["readme", *(["--write"] if write else []), str(directory)]) == 1
    out = capsys.readouterr().out
    assert "error: SZZ-0005: Cannot read README.md: it is not UTF-8 (byte 0xe9 at position 15); save it as UTF-8." in out
    assert "1 unreadable" in out
    assert (directory / "README.md").read_bytes() == stored


# --- the lint reads the README the same way --------------------------------------------------

def _lint_codes(scenario: Path) -> list[tuple[str, str]]:
    from szzbench.graph_validator import validate_graph_scenario_file
    from szzbench.validator import validate_scenario_file

    if scenario.name == "scenario.graph.yml":
        _, result = validate_graph_scenario_file(scenario, strict_paths=True, lint=True)
    else:
        _, result, _ = validate_scenario_file(scenario, lint=True)
    return [(f.code, f.message) for f in result.findings if f.code.endswith("455")]


@pytest.mark.parametrize("scenario,code", [(CLASSIC, "W455"), (GRAPH, "GW455")], ids=["classic", "graph"])
def test_the_lint_reports_a_doubled_and_a_malformed_header(tmp_path, scenario, code):
    text, header, body = _shipped(scenario)
    directory = _copy(tmp_path, scenario, header + "\n" + header + body)
    path = directory / scenario.name
    findings = _lint_codes(path)
    assert [c for c, _ in findings] == [code] and "README carries a second header at line" in findings[0][1]
    (directory / "README.md").write_text(text.replace(HEADER_END + "\n", "", 1), encoding="utf-8")
    findings = _lint_codes(path)
    assert findings == [(code, "README header is malformed: no end marker after the table; "
                               "run `szzbench readme --write`.")]
    assert main(["readme", "--write", str(directory)]) == 0
    assert _lint_codes(path) == []
    (directory / "README.md").write_bytes(("﻿" + _crlf(text)).encode("utf-8"))
    assert _lint_codes(path) == [], "a BOM and CRLF endings are not a W455"


# --- the shipped suites ------------------------------------------------------------------------

def test_writing_a_current_shipped_readme_changes_no_byte():
    unchanged = []
    for scenario in scenario_files(REPO / "scenarios", REPO / "advanced-scenarios"):
        data, _ = load_yaml(scenario)
        text = scenario.with_name("README.md").read_bytes().decode("utf-8")
        unchanged.append(apply_header(text, render_header(data, suite_of(scenario))) == text)
    assert unchanged and all(unchanged)
