"""README.md describes the CLI, the package and the tool setup as they are (issues #202 and #193).

`README.md` had drifted from the code it documents: `validate-index`,
`baselines` and `coverage` had no section, options of `build_parser()` such as
`--family`, `--out-root` and `--slug` appeared nowhere, and the directory tree
listed seventeen of the twenty-eight Python files under `src/szzbench/`.
These tests compare the README with the code: every subcommand has a section
headed with its name, that section names each of the subcommand's options,
and the tree names every module. Page links must name existing headings.

The Scenario Editor declared all ten of its dependencies as `latest`, and the
READMEs set both web tools up with `npm install`, which may resolve the ranges
afresh and rewrite the lock (issue #193).  The last two tests check that each
tool's `package.json` names versions, that its lock records the same ranges,
and that the setup commands use `npm ci`, which installs what the lock records.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from szzbench.cli import build_parser

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"
TOOLS = ("scenario-editor", "generated-repo-viewer")
FENCE = re.compile(r"^ {0,3}```")


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """Heading positions, levels and text, ignoring lines inside code blocks."""
    headings: list[tuple[int, int, str]] = []
    in_block = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            in_block = not in_block
        elif not in_block and (match := re.match(r"^(#{1,6}) (.+)$", line)):
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    assert not in_block, "unclosed code fence"
    return headings


def _sections(lines: list[str]) -> dict[str, list[str]]:
    """Each heading's text, and the sections it heads: the text up to the next
    heading of the same or a higher level."""
    headings = _headings(lines)
    sections: dict[str, list[str]] = {}
    for position, (start, level, text) in enumerate(headings):
        end = next((index for index, other, _ in headings[position + 1:] if other <= level), len(lines))
        sections.setdefault(text, []).append("\n".join(lines[start:end]))
    return sections


def _code_blocks(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if FENCE.match(line):
            if current is None:
                current = []
            else:
                blocks.append(current)
                current = None
        elif current is not None:
            current.append(line)
    return blocks


def _commands() -> dict[str, list[str]]:
    """Each subcommand of `build_parser()` and its option strings, `--help` left out."""
    parser = build_parser()
    subparsers = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    return {name: [option for action in command._actions if not isinstance(action, argparse._HelpAction)
                   for option in action.option_strings]
            for name, command in subparsers.choices.items()}


def test_every_command_has_a_section_that_names_each_of_its_options():
    problems = []
    sections = _sections(README.read_text(encoding="utf-8").splitlines())
    for command, options in _commands().items():
        found = sections.get(command, [])
        if len(found) != 1:
            problems.append(f"the README has {len(found)} sections headed `{command}`")
            continue
        # `--out` is not named by `--out-root`, nor `--strict` by `--strict-paths`
        missing = [option for option in options
                   if not re.search(rf"(?<![\w-]){re.escape(option)}(?![\w-])", found[0])]
        if missing:
            problems.append(f"the section `{command}` does not name {', '.join(missing)}")
    assert problems == []


def test_the_directory_tree_names_every_module_of_the_package():
    modules = sorted(path.name for path in (REPO / "src" / "szzbench").glob("*.py"))
    lines = README.read_text(encoding="utf-8").splitlines()
    trees = [block for block in _code_blocks(lines) if block and block[0] == "SZZBench/"]
    assert len(trees) == 1, f"the README has {len(trees)} directory trees"
    listed = {match.group(1) for line in trees[0] if (match := re.search(r"[├└]── (\S+\.py)$", line))}
    assert [module for module in modules if module not in listed] == [], "the tree lacks these modules"


def test_the_readme_links_to_existing_headings():
    lines = README.read_text(encoding="utf-8").splitlines()
    anchors = set()
    seen: Counter[str] = Counter()
    for _, _, heading in _headings(lines):
        anchor = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        anchors.add(f"{anchor}-{seen[anchor]}" if seen[anchor] else anchor)
        seen[anchor] += 1
    targets = re.findall(r"\]\((#[^)\s]+)\)", "\n".join(lines))
    assert [target for target in targets if target[1:] not in anchors] == [], "links to missing headings"


def test_each_tool_names_its_dependency_versions_and_its_lock_records_the_same_ranges():
    for tool in TOOLS:
        directory = REPO / "tools" / tool
        manifest = json.loads((directory / "package.json").read_text(encoding="utf-8"))
        locked = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))["packages"][""]
        for group in ("dependencies", "devDependencies"):
            ranges = manifest.get(group, {})
            # a dist-tag such as `latest`, or `*`, names no version
            assert {name: spec for name, spec in ranges.items() if not re.search(r"\d", spec)} == {}, \
                f"tools/{tool}/package.json: {group} without a version"
            assert locked.get(group, {}) == ranges, f"tools/{tool}/package-lock.json records other {group} ranges"


def test_the_readmes_set_the_tools_up_with_npm_ci():
    for path in (README, *(REPO / "tools" / tool / "README.md" for tool in TOOLS)):
        setups = [block for block in _code_blocks(path.read_text(encoding="utf-8").split("\n"))
                  if "npm run dev" in block]
        assert setups, f"{path.relative_to(REPO)} shows no setup"
        for block in setups:
            commands = [line.strip() for line in block]
            assert "npm ci" in commands and not any(re.match(r"npm (install|i)\b", line) for line in commands), \
                f"{path.relative_to(REPO)}: {commands}"
