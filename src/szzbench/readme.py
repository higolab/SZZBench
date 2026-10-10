"""The generated header of a scenario README (issue #19).

Every scenario README opens with a header that is **rendered from the scenario
file**: the ``# <id>: <title>`` line and a metadata table between two marker
comments.  The header is the only part of a README a tool writes.  Everything
after the end marker is the author's prose -- purpose, evidence, what a tool
must do -- and is never touched.

The header replaces the hand-written copies that drifted: ``## Factors`` lists
that no longer matched ``meta.factors`` (8 of 251 on 2026-09-22), ``## Source``
sections naming a category vocabulary the index had abandoned (35), and, in the
graph suite, a boilerplate sentence about "graph-aware semantics" in place of
the features a scenario actually uses.

``szzbench readme`` checks every README against its scenario (exit 1 when a
header is missing or stale) and ``--write`` regenerates them; ``validate
--lint`` reports the same disagreement as ``W455`` / ``GW455``.

A header edited out of its exact shape is *malformed*, not missing: ``--write``
replaces the whole old header rather than stacking a new one above it, and a
second header left in the body is stale (issue #184).  A UTF-8 BOM and CRLF
line endings are not a difference; ``--write`` keeps both.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .operations import SUPPORTED_OPERATIONS
from .scenario import load_yaml

HEADER_BEGIN = ("<!-- szzbench:header (generated from the scenario file: edit the YAML "
                "and run `szzbench readme --write`) -->")
HEADER_END = "<!-- /szzbench:header -->"

#: Hand-written copies of header data.  ``## Factors`` repeated ``meta.factors``
#: and ``## Source`` carried a ``- Category:`` label; both are removed when the
#: header is written and reported by the lint while they remain.
LEGACY_HEADING_RE = re.compile(r"^## (Factors|Source)[ \t]*$")
HEADING_RE = re.compile(r"^#{1,6} ")
#: Fenced code blocks, by the CommonMark rules that matter here.  A block opens
#: with three or more backticks or tildes indented at most three spaces, followed
#: by an info string (which may not contain a backtick after a backtick fence).
#: It closes with a fence of the same character, at least as long, indented at
#: most three spaces, and followed by nothing but spaces or tabs -- so a line
#: such as ``~~~literal`` inside a tilde block is content, not the closing fence.
#: Headings inside a block are text, not sections.
OPEN_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CLOSE_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
#: A line meant as a header marker however it is spelled: an HTML comment
#: opening with ``szzbench:header`` (begin) or ``/szzbench:header`` (end), in
#: any case, with any whitespace inside it and anything after it (issue #184).
#: It is indented by at most three spaces, as Markdown's HTML blocks are: a line
#: indented further, or by a tab, is indented code, which quotes a marker as
#: text (PR #222 review).
MARKER_LINE_RE = re.compile(r"^ {0,3}<!--\s*(/?)\s*szzbench\s*:\s*header\b", re.IGNORECASE)
BOM = "\ufeff"

#: ``expected_szz`` sections the classic schema does not have.
GRAPH_ONLY_ORACLE_LEVELS = ("entity_level", "branch_level", "work_item_level", "bug_level")

#: Top-level context sections the classic schema does not have.
GRAPH_CONTEXT_SECTIONS = ("issues", "work_items", "developer_hints", "clone_relationships",
                          "copy_relationships", "bug_instances", "bug_groups", "semantic_rewrites",
                          "fix_series", "context")

#: Per-commit keys that record a replayed or rewritten commit.
REPLAY_KEYS = (("rebase_of", "rebase"), ("cherry_pick_of", "cherry-pick"), ("backport_of", "backport"),
               ("revert_of", "revert"), ("squash_of", "squash"), ("apply_squash", "squash"),
               ("apply_patch_from", "patch replay"))


def suite_of(scenario_path: Path) -> str:
    """The evaluator's suite name for a scenario file."""
    return "advanced-scenarios" if scenario_path.name == "scenario.graph.yml" else "scenarios"


# --- rendering -----------------------------------------------------------------

def _code(value: Any) -> str:
    return f"`{value}`"


def _codes(values: list[str]) -> str:
    return ", ".join(_code(v) for v in values)


def _policy_phrase(policy: Any) -> str:
    parts = [_code(policy.evaluation_policy)]
    if policy.expect_no_bic:
        parts.append("expects no BIC")
    elif policy.evaluation_policy == "top_k":
        parts.append("relevant " + (_codes(policy.relevant) if policy.relevant else _codes(policy.required)))
        if policy.k_values:
            parts.append("k = " + ", ".join(str(k) for k in policy.k_values))
        if policy.status_k is not None:
            parts.append(f"status at k = {policy.status_k}")
    else:
        parts.append("required " + (_codes(policy.required) if policy.required else "none"))
    if policy.minimum_required is not None:
        parts.append(f"minimum {policy.minimum_required}")
    if policy.acceptable_related:
        parts.append("acceptable " + ", ".join(
            _code(entry.commit) + (f" (credit {entry.credit:g})" if entry.credit else "")
            for entry in policy.acceptable_related))
    if policy.related_origins:
        parts.append("related origins " + _codes(policy.related_origins))
    if policy.related_but_not_correct:
        parts.append("related but not correct " + _codes(policy.related_but_not_correct))
    if policy.known_distractors:
        parts.append("known distractors " + _codes(policy.known_distractors))
    return "; ".join(parts)


def oracle_summary(data: dict[str, Any], suite: str) -> str:
    """The commit-level oracle the evaluator resolves, variant by variant.

    Read through ``_commit_level_policy`` so a default variant, an inferred
    direct BIC or a ``top_k`` oracle appears exactly as a scored run sees it.
    """
    from .evaluator import _commit_level_policy, _scenario_bfc_ids

    default = _commit_level_policy(data, suite, None)
    expected_szz = data.get("expected_szz") if isinstance(data.get("expected_szz"), dict) else {}
    variants = [v for v in (expected_szz.get("evaluation_variants") or []) if isinstance(v, dict) and v.get("name")]
    if variants:
        label = "default"
        if default.evaluation_variant:
            label += f" ({_code(default.evaluation_variant)})"
        pieces = [f"{label}: {_policy_phrase(default)}"]
        for variant in variants:
            if variant["name"] == default.evaluation_variant:
                continue
            pieces.append(f"{_code(variant['name'])}: {_policy_phrase(_commit_level_policy(data, suite, variant['name']))}")
        summary = " · ".join(pieces)
    else:
        summary = _policy_phrase(default)
    bfcs = _scenario_bfc_ids(data)
    if bfcs:
        summary += f" · {'BFC' if len(bfcs) == 1 else 'BFCs'} {_codes(bfcs)}"
    branch_level = expected_szz.get("branch_level")
    if isinstance(branch_level, dict) and branch_level:
        parts = []
        for name, spec in branch_level.items():
            if not isinstance(spec, dict):
                continue
            required = [r for r in (spec.get("required") or []) if isinstance(r, str)]
            parts.append(f"{name} → {_codes(required) if required else 'none'} (BFC {_code(spec.get('bfc'))})")
        if parts:
            summary += " · branch-level: " + "; ".join(parts)
    return summary


def graph_features(data: dict[str, Any]) -> list[str]:
    """What a graph scenario uses that the classic schema cannot express.

    The classic schema is a linear ``main`` history of ``write_file`` /
    ``replace`` operations with one bug per scenario and a commit-level
    exact-set oracle; everything else is a reason for a scenario to live in
    the graph suite, and this lists the ones a scenario actually has.
    """
    commits = [c for c in (data.get("commits") or []) if isinstance(c, dict)]
    features: list[str] = []

    branches: list[str] = []
    for commit in commits:
        branch = commit.get("branch")
        if isinstance(branch, str) and branch not in branches:
            branches.append(branch)
    if len(branches) > 1:
        features.append(f"{len(branches)} branches")
    merges = [str(c.get("id")) for c in commits if len(c.get("parents") or []) > 1]
    if merges:
        features.append(("merge commit " if len(merges) == 1 else "merge commits ") + _codes(merges))
    for key, label in REPLAY_KEYS:
        ids = [str(c.get("id")) for c in commits if key in c]
        if ids:
            features.append(f"{label} {_codes(ids)}")
    operations: list[str] = []
    for commit in commits:
        for op in commit.get("operations") or []:
            kind = op.get("type") if isinstance(op, dict) else None
            if isinstance(kind, str) and kind not in SUPPORTED_OPERATIONS and kind not in operations:
                operations.append(kind)
    generated = (data.get("commit_generators") or any("commit_generator" in c for c in commits)
                 or "commit_generator" in operations)
    operations = [kind for kind in operations if kind != "commit_generator"]
    if generated:
        features.append("generated commits (`commit_generator`)")
    graph = data.get("graph") if isinstance(data.get("graph"), dict) else {}
    if graph.get("ref_lifecycle"):
        features.append("ref lifecycle")
    if operations:
        features.append(("operation " if len(operations) == 1 else "operations ") + _codes(operations))

    from .graph_scenario import graph_bfc_entries, graph_bic_entries, graph_faults

    bugs = [b for b in (data.get("bugs") or []) if isinstance(b, dict)]
    if len(bugs) > 1:
        features.append(f"{len(bugs)} bugs")
    most_bics = max((len(graph_bic_entries(b)) for b in bugs), default=0)
    if most_bics > 1:
        features.append(f"{most_bics} BICs")
    most_bfcs = max((len(graph_bfc_entries(b)) for b in bugs), default=0)
    if most_bfcs > 1:
        features.append(f"{most_bfcs} BFCs")
    if any(b.get("origin_faults") for b in bugs):
        features.append("origin faults")
    most_faults = max((len(graph_faults(b)) for b in bugs), default=0)
    if most_faults > 1:
        features.append(f"{most_faults} fault sites")

    expected_szz = data.get("expected_szz") if isinstance(data.get("expected_szz"), dict) else {}
    commit_level = expected_szz.get("commit_level") if isinstance(expected_szz.get("commit_level"), dict) else {}
    policy = commit_level.get("evaluation_policy")
    if isinstance(policy, str) and policy != "exact_set":
        features.append(f"policy {_code(policy)}")
    variants = [v.get("name") for v in (expected_szz.get("evaluation_variants") or []) if isinstance(v, dict)]
    if variants:
        noun = "evaluation variant" if len(variants) == 1 else "evaluation variants"
        features.append(f"{len(variants)} {noun} ({_codes([str(v) for v in variants])})")
    for level in GRAPH_ONLY_ORACLE_LEVELS:
        if expected_szz.get(level):
            features.append(f"{_code(level)} oracle")
    for section in GRAPH_CONTEXT_SECTIONS:
        if data.get(section):
            features.append(_code(section))
    return features


NO_GRAPH_FEATURE = ("none: a linear history with one bug and an exact-set oracle, "
                    "kept in the graph suite for its category")


def header_rows(data: dict[str, Any], suite: str) -> list[tuple[str, str]]:
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else {}
    code = meta.get("category_code")
    name = meta.get("category")
    category = " ".join(part for part in (_code(code) if code else "", str(name) if name else "") if part) or "—"
    factors = [f for f in (meta.get("factors") or []) if isinstance(f, str)]
    rows = [
        ("category", category),
        ("tier", _code(meta.get("tier")) if meta.get("tier") else "—"),
        ("status", _code(meta.get("status")) if meta.get("status") else "—"),
        ("difficulty", _code(meta.get("difficulty")) if meta.get("difficulty") else "—"),
        ("language", _code(repository.get("language")) if repository.get("language") else "—"),
        ("factors", _codes(factors) if factors else "—"),
        ("oracle", oracle_summary(data, suite)),
    ]
    if isinstance(meta.get("defeats"), list):
        defeats = [d for d in meta["defeats"] if isinstance(d, str)]
        rows.append(("defeats", _codes(defeats) if defeats else "none (a control: every declared cheap rule may solve it)"))
    if suite == "advanced-scenarios":
        features = graph_features(data)
        rows.append(("graph features", "; ".join(features) if features else NO_GRAPH_FEATURE))
    return rows


def render_header(data: dict[str, Any], suite: str) -> str:
    """The exact text a README must start with.

    The title is put on one line: a line break or a run of whitespace in
    ``meta.title`` becomes one space, so the header keeps the shape it is
    recognised by (issue #184).
    """
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    title = " ".join(str(meta.get("title", "")).split())
    lines = [f"# {meta.get('id')}: {title}", "", HEADER_BEGIN, "| | |", "|---|---|"]
    for key, value in header_rows(data, suite):
        lines.append(f"| {key} | {value} |")
    lines.append(HEADER_END)
    return "\n".join(lines) + "\n"


# --- checking and applying -----------------------------------------------------

HEADER_SHAPE_RE = re.compile(
    r"\A# [^\n]*\n\n" + re.escape(HEADER_BEGIN) + r"\n(?:\|[^\n]*\n)+" + re.escape(HEADER_END) + r"\n?")


def split_header(text: str) -> tuple[str | None, str]:
    """``(header, rest)``: the generated header a README opens with, or ``None``.

    ``rest`` starts right after the end marker's line and is returned exactly
    as the file has it, blank lines included.
    """
    match = HEADER_SHAPE_RE.match(text)
    if match is None:
        return None, text
    return match.group(0), text[match.end():]


def _outside_fences(lines: list[str]) -> list[bool]:
    """Per line, whether it is outside fenced code; a fence line itself is inside.

    ``lines`` may keep their endings, ``\\n`` or ``\\r\\n``.
    """
    flags: list[bool] = []
    fence: str | None = None
    for line in lines:
        content = line.rstrip("\r\n")
        if fence is not None:
            closing = CLOSE_FENCE_RE.match(content)
            if closing and closing.group(1)[0] == fence[0] and len(closing.group(1)) >= len(fence):
                fence = None
            flags.append(False)           # every line inside a block is content
            continue
        opening = OPEN_FENCE_RE.match(content)
        if opening and not (opening.group(1)[0] == "`" and "`" in opening.group(2)):
            fence = opening.group(1)
            flags.append(False)
            continue
        flags.append(True)
    return flags


def legacy_sections(text: str) -> list[tuple[int, int, str]]:
    """``(first_line, end_line, title)`` of every real ``## Factors`` / ``## Source`` section.

    Real means outside fenced code: a heading quoted inside a code example is
    text, and a fenced block inside a section does not end the section.  A
    section runs to the next heading outside fenced code, or to the end.
    """
    lines = text.splitlines(keepends=True)
    found: list[tuple[int, int, str]] = []
    current: tuple[int, str] | None = None
    for index, outside in enumerate(_outside_fences(lines)):
        line = lines[index].rstrip("\r\n")
        if not outside or not HEADING_RE.match(line):
            continue
        if current is not None:
            found.append((current[0], index, current[1]))
            current = None
        legacy = LEGACY_HEADING_RE.match(line)
        if legacy:
            current = (index, legacy.group(1))
    if current is not None:
        found.append((current[0], len(lines), current[1]))
    return found


def remove_legacy_sections(text: str) -> str:
    """``text`` without its real legacy sections; every other byte is kept.

    The only spacing touched is at a removal boundary: a section removed from
    the end of the file takes the blank lines that separated it from the prose
    before it, so the file still ends with a single newline.
    """
    sections = legacy_sections(text)
    if not sections:
        return text
    lines = text.splitlines(keepends=True)
    for first, end, _ in reversed(sections):
        del lines[first:end]
        if first >= len(lines):
            while len(lines) > 1 and not lines[-1].strip():
                lines.pop()
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
    return "".join(lines)


# --- finding an old header by its markers (issue #184) ---------------------------

#: Said of a malformed header when no narrower reason applies.
SHAPE_REASON = ("it is not the generated shape: the title line, one blank line, the begin marker, "
                "table rows, the end marker")


def _split_lines(text: str) -> list[str]:
    """``text`` cut after every ``\\n``, endings kept, so the pieces join back to ``text``.

    Only ``\\n`` ends a line, as in ``HEADER_SHAPE_RE``; ``str.splitlines``
    would also cut at a form feed or a Unicode line separator.
    """
    pieces = text.split("\n")
    lines = [piece + "\n" for piece in pieces[:-1]]
    if pieces[-1]:
        lines.append(pieces[-1])
    return lines


def _content(line: str) -> str:
    """A line without its ``\\n`` or ``\\r\\n``."""
    if line.endswith("\r\n"):
        return line[:-2]
    return line[:-1] if line.endswith("\n") else line


def _normalized(text: str) -> str:
    """``text`` as it is compared: without a leading BOM, with LF line endings."""
    return (text[1:] if text.startswith(BOM) else text).replace("\r\n", "\n")


def _marker(content: str) -> str | None:
    """``"begin"`` or ``"end"`` for a line meant as a header marker, else ``None``."""
    match = MARKER_LINE_RE.match(content)
    if match is None:
        return None
    return "end" if match.group(1) else "begin"


def _is_row(content: str) -> bool:
    return content.startswith("|")


def _is_title(content: str) -> bool:
    return content.lstrip(BOM).startswith("# ")


def _table_after(contents: list[str], begin: int) -> tuple[list[int], int]:
    """The table rows under a begin marker, and the line the table stops at.

    Blank lines are passed over, so a blank line inside the table does not cut
    it short; the line it stops at is neither a row nor blank.
    """
    rows: list[int] = []
    index = begin + 1
    while index < len(contents) and (_is_row(contents[index]) or not contents[index].strip()):
        if _is_row(contents[index]):
            rows.append(index)
        index += 1
    return rows, index


def _misspelled(kind: str, have: str, want: str) -> str:
    if have.strip() == want:
        side = "trailing" if have.startswith(want) else "leading" if have.endswith(want) else "leading and trailing"
        return f"the {kind} marker has {side} whitespace"
    return f"the {kind} marker reads {have!r}, not {want!r}"


def _trimmed(contents: list[str], first: int, end: int) -> tuple[int, int] | None:
    """``(first, end)`` without the blank lines at either edge; ``None`` when nothing is left."""
    while first < end and not contents[first].strip():
        first += 1
    while end > first and not contents[end - 1].strip():
        end -= 1
    return (first, end) if first < end else None


@dataclass
class HeaderRegion:
    """The old header at the top of a README, found by its markers.

    ``end`` is the first line after it.  ``reasons`` says how it departs from
    the generated shape.  ``kept`` lists the author's text inside it -- above
    the title line, or between the title line and the begin marker -- as
    ``(first, end)`` line ranges, which ``apply_header`` moves under the new
    header instead of dropping.
    """
    end: int
    reasons: list[str]
    kept: list[tuple[int, int]]


def header_region(contents: list[str]) -> HeaderRegion | None:
    """The old header a README opens with, however malformed; ``None`` without one.

    ``contents`` are the README's lines without their endings.  The header is
    found by its first marker line outside fenced code, whatever its spelling.
    It runs from the start of the file through the end marker, or through the
    last table row when the end marker is missing.
    """
    outside = _outside_fences(contents)
    first = next((i for i, content in enumerate(contents) if outside[i] and _marker(content)), None)
    if first is None:
        return None
    begin: int | None
    end_marker: int | None
    if _marker(contents[first]) == "begin":
        top = begin = first
        rows, stop = _table_after(contents, begin)
        end_marker = stop if stop < len(contents) and _marker(contents[stop]) == "end" else None
        end = end_marker + 1 if end_marker is not None else (rows[-1] if rows else begin) + 1
    else:
        begin, end_marker, end = None, first, first + 1
        rows = []
        index = first - 1
        while index >= 0 and (_is_row(contents[index]) or not contents[index].strip()):
            if _is_row(contents[index]):
                rows.insert(0, index)
            index -= 1
        top = rows[0] if rows else first

    reasons: list[str] = []
    title = next((i for i in range(top - 1, -1, -1) if outside[i] and _is_title(contents[i])), None)
    if title is None:
        reasons.append("no `# <id>: <title>` line above the begin marker")
        kept = [(0, top)]
    else:
        above, between = range(0, title), range(title + 1, top)
        if any(contents[i].strip() for i in above):
            reasons.append("text before the title line")
        elif above:
            reasons.append(f"{len(above)} blank line{'s' if len(above) > 1 else ''} before the title line")
        if any(contents[i].strip() for i in between):
            reasons.append("text between the title line and the begin marker")
        elif not between:
            reasons.append("no blank line between the title line and the begin marker")
        elif len(between) > 1:
            reasons.append(f"{len(between)} blank lines between the title line and the begin marker, not one")
        elif contents[title + 1]:
            reasons.append("whitespace on the blank line between the title line and the begin marker")
        kept = [(0, title), (title + 1, top)]
    if begin is None:
        reasons.append("no begin marker above the table" if rows else "no begin marker above the end marker")
    elif contents[begin] != HEADER_BEGIN:
        reasons.append(_misspelled("begin", contents[begin], HEADER_BEGIN))
    if not rows:
        reasons.append("no table rows")
    last = end_marker if end_marker is not None else end - 1
    if any(not contents[i].strip() for i in range(top + 1, last)):
        reasons.append("a blank line inside the table")
    if end_marker is None:
        reasons.append("no end marker after the table")
    elif contents[end_marker] != HEADER_END:
        reasons.append(_misspelled("end", contents[end_marker], HEADER_END))
    trimmed = [_trimmed(contents, a, b) for a, b in kept]
    return HeaderRegion(end=end, reasons=reasons, kept=[r for r in trimmed if r is not None])


def extra_headers(contents: list[str]) -> list[tuple[int, int, int, str]]:
    """``(first, end, marker, kind)`` of every header marker in a README body.

    Only markers outside fenced code count.  A begin marker (``kind``
    ``"header"``) brings its table, its end marker and the ``# `` title line
    above it: the leftover of an old header.  An end marker on its own
    (``kind`` ``"end marker"``) is a stray one.  ``marker`` is the marker's
    line.
    """
    outside = _outside_fences(contents)
    found: list[tuple[int, int, int, str]] = []
    index = 0
    while index < len(contents):
        kind = _marker(contents[index]) if outside[index] else None
        if kind is None:
            index += 1
            continue
        first, end = index, index + 1
        if kind == "begin":
            rows, stop = _table_after(contents, index)
            if stop < len(contents) and _marker(contents[stop]) == "end":
                end = stop + 1
            elif rows:
                end = rows[-1] + 1
            above = index - 1
            while above >= 0 and not contents[above].strip():
                above -= 1
            if above >= 0 and outside[above] and _is_title(contents[above]):
                first = above
        found.append((first, end, index, "header" if kind == "begin" else "end marker"))
        index = end
    return found


def remove_extra_headers(text: str) -> str:
    """``text`` without the header leftovers ``extra_headers`` finds; every other byte is kept.

    A leftover takes the blank lines under it, so the prose around it keeps
    one separation; one at the end of the file takes the blank lines above it.
    """
    lines = _split_lines(text)
    blocks = extra_headers([_content(line) for line in lines])
    for first, end, _, _ in reversed(blocks):
        while end < len(lines) and not lines[end].strip():
            end += 1
        del lines[first:end]
        if first >= len(lines):
            while len(lines) > 1 and not lines[-1].strip():
                lines.pop()
    return "".join(lines)


def _opens_with_blank_line(text: str) -> bool:
    return text.startswith("\n") or text.startswith("\r\n")


def check_readme(text: str, header: str) -> list[str]:
    """Why a README disagrees with its scenario; empty when it agrees.

    A leading UTF-8 BOM and CRLF line endings are not a disagreement: the file
    is compared without the one and with LF for the other (issue #184).
    """
    problems: list[str] = []
    normalized = _normalized(text)
    lines = _split_lines(normalized)
    region = header_region([_content(line) for line in lines])
    existing, rest = split_header(normalized)
    if existing is None and region is None:
        problems.append("has no generated header")
    elif existing is None:
        problems.append("header is malformed: " + "; ".join(region.reasons or [SHAPE_REASON]))
    elif existing != header:
        for have, want in zip(existing.splitlines(), header.splitlines()):
            if have != want:
                problems.append(f"header is stale: {have!r} should read {want!r}")
                break
        else:
            problems.append("header is stale: the two differ in length")
    if region is not None:
        rest = "".join(lines[region.end:])
        for _, _, marker, kind in extra_headers([_content(line) for line in lines[region.end:]]):
            what = "a second header" if kind == "header" else "a stray header end marker"
            problems.append(f"carries {what} at line {region.end + marker + 1}, a leftover of an old header")
    for _, _, title in legacy_sections(rest):
        problems.append(f"carries a `## {title}` section, a hand-written copy of what the header states")
    return problems


def _strip_leading_title(text: str) -> str:
    """The body of a README that has no header yet: everything after its
    ``# <id>: <title>`` line and the blank lines that follow it."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "".join(lines)


def apply_header(text: str, header: str) -> str:
    """The README with ``header`` in place and the real legacy copies removed.

    The author's body is preserved byte for byte: on a first write the old
    title line and the blank lines under it make room for the header, and on
    an update only the header is replaced.  Nothing after the end marker is
    reflowed or re-spaced except at the boundary of a removed legacy section.

    A malformed header is replaced whole, from the start of the file through
    its end marker, or through its last table row when the end marker is
    missing, so exactly one header remains; text the author had put above its
    title line, or between that line and the begin marker, becomes the first
    paragraph of the body.  A second header in the body is removed the way a
    legacy section is.  A leading BOM and the file's line endings (those of
    its first line) are kept: the header is written with them (issue #184).
    """
    bom = BOM if text.startswith(BOM) else ""
    text = text[len(bom):]
    first_break = text.find("\n")
    newline = "\r\n" if first_break > 0 and text[first_break - 1] == "\r" else "\n"
    lines = _split_lines(text)
    region = header_region([_content(line) for line in lines])
    if region is None:
        rest = _strip_leading_title(text)
        if rest:
            rest = newline + rest
    else:
        rest = "".join(lines[region.end:])
        kept = newline.join("".join(lines[first:end]) for first, end in region.kept)
        if kept:
            rest = kept + (newline + rest if rest and not _opens_with_blank_line(rest) else rest)
    rest = remove_legacy_sections(remove_extra_headers(rest))
    header = header.replace("\n", newline)
    if not rest.strip():
        return bom + header
    if not _opens_with_blank_line(rest):
        rest = newline + rest
    return bom + header + rest


# --- running over the suites ------------------------------------------------

@dataclass
class ReadmeStatus:
    scenario_id: str
    readme: Path
    problems: list[str] = field(default_factory=list)
    written: bool = False
    #: What ``--write`` left wrong: the problems found in the file it wrote,
    #: or why it did not write (issue #184).
    unresolved: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"scenario_id": self.scenario_id, "readme": str(self.readme), "problems": self.problems,
                "written": self.written, "unresolved": self.unresolved, "error": self.error}


def scenario_files(scenarios_root: Path, advanced_scenarios_root: Path) -> list[Path]:
    files = sorted(scenarios_root.glob("SZZ-*/scenario.yml"))
    files += sorted(advanced_scenarios_root.glob("SZZG-*/scenario.graph.yml"))
    return files


def resolve_targets(targets: list[str]) -> list[Path]:
    """Scenario files named on the command line, directly or by directory.

    A scenario directory gives the scenario file in it.  A directory without
    one -- a suite root such as ``scenarios/`` -- gives the scenarios under it
    as ``scenario_files`` finds them in a root, so ``readme scenarios`` checks
    what ``readme`` without arguments checks of that suite.  A directory that
    gives neither is kept as it is and reported by ``sync_readme``; it counted
    as zero scenarios, and the command passed having checked nothing (issue #188).
    """
    files: list[Path] = []
    for raw in targets:
        path = Path(raw)
        if path.is_dir():
            found = [path / name for name in ("scenario.yml", "scenario.graph.yml") if (path / name).exists()]
            files += found or scenario_files(path, path) or [path]
        else:
            files.append(path)
    return files


#: Why a directory target is an error: ``resolve_targets`` found no scenario in it (issue #188).
NO_SCENARIO_FILE = ("no scenario file found: it holds no scenario.yml or scenario.graph.yml, and no "
                    "SZZ-*/scenario.yml or SZZG-*/scenario.graph.yml directly under it")


#: Why a stale README is left as it is: its header would not be found again.
NOT_WRITABLE = ("the header rendered from the scenario file is not one title line and one table row per field "
                "(a value has a line break); fix the scenario file")


def sync_readme(scenario_path: Path, *, write: bool) -> ReadmeStatus:
    """Check one README against its scenario; rewrite it when ``write``.

    The README is read as stored, so a BOM and CRLF endings survive a write.
    What is written is read back and checked again, and what is still wrong
    is kept in ``unresolved``; a header the scenario renders out of shape (a
    value with a line break) is not written at all, because the next write
    could not find where it ends (issue #184).  A directory is one
    ``resolve_targets`` found no scenario in, and is an error (issue #188).
    """
    if scenario_path.is_dir():
        return ReadmeStatus(scenario_id=str(scenario_path), readme=scenario_path / "README.md",
                            error=NO_SCENARIO_FILE)
    readme = scenario_path.with_name("README.md")
    # A missing file is named by its path: a bare name has no directory to name it by, and the
    # directory above a mistyped scenario directory is the suite root (issue #188).
    scenario_id = scenario_path.parent.name if scenario_path.exists() else str(scenario_path)
    status = ReadmeStatus(scenario_id=scenario_id, readme=readme)
    data, result = load_yaml(scenario_path)
    if data is None:
        status.error = "; ".join(f.message for f in result.findings)
        return status
    header = render_header(data, suite_of(scenario_path))
    try:
        text = readme.read_bytes().decode("utf-8") if readme.exists() else ""
    except UnicodeDecodeError as exc:
        # A README that is not UTF-8 ended in a traceback (issue #184).
        status.error = (f"Cannot read {readme.name}: it is not UTF-8 (byte 0x{exc.object[exc.start]:02x} at "
                        f"position {exc.start}); save it as UTF-8.")
        return status
    except OSError as exc:
        status.error = f"Cannot read {readme.name}: {exc}"
        return status
    status.problems = check_readme(text, header) if text else ["is missing"]
    if status.problems and write:
        if HEADER_SHAPE_RE.fullmatch(header) is None:
            status.unresolved = [NOT_WRITABLE]
            return status
        readme.write_text(apply_header(text, header), encoding="utf-8", newline="")
        status.written = True
        status.unresolved = check_readme(readme.read_bytes().decode("utf-8"), header)
    return status


def run_readme(files: list[Path], *, write: bool) -> dict[str, Any]:
    statuses = [sync_readme(path, write=write) for path in files]
    return {
        "scenario_count": len(statuses),
        "current": sum(1 for s in statuses if not s.problems and s.error is None),
        "written": sum(1 for s in statuses if s.written),
        "stale": [s.to_dict() for s in statuses if s.problems],
        "unresolved": [s.to_dict() for s in statuses if s.unresolved],
        "errors": [s.to_dict() for s in statuses if s.error],
    }


def format_readme_report(report: dict[str, Any], *, write: bool) -> str:
    lines = []
    for item in report["stale"]:
        verb = "rewrote" if item["written"] else "stale"
        lines.append(f"{verb}: {item['readme']}")
        for problem in item["problems"]:
            lines.append(f"    {problem}")
        if item["unresolved"]:
            lines.append("    still stale after the write:" if item["written"] else "    not written:")
            lines.extend(f"        {problem}" for problem in item["unresolved"])
    for item in report["errors"]:
        lines.append(f"error: {item['scenario_id']}: {item['error']}")
    summary = (f"{report['scenario_count']} scenario(s): {report['current']} README header(s) current, "
               f"{report['written'] if write else len(report['stale'])} {'rewritten' if write else 'stale or missing'}, "
               f"{len(report['errors'])} unreadable")
    if report["unresolved"]:
        summary += f"; {len(report['unresolved'])} still stale"
    lines.append(summary)
    return "\n".join(lines)
