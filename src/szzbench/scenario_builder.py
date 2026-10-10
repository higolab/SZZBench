from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

from .findings import ValidationResult
from .index_splice import IndexSpliceError, read_index_text, splice_index_entry, write_index_text
from .retired_ids import read_retired_ids
from .scenario import load_yaml
from .validator import (DEFEATABLE_FAMILIES, INDEX_ENTRY_KEYS, SCENARIO_DIFFICULTIES, SCENARIO_TIERS, lint_factors,
                        load_index)

DEFAULT_SCENARIOS_ROOT = Path("scenarios")
SCENARIO_ID_RE = re.compile(r"^SZZ-(\d+)$")
VOCABULARY = "docs/decisions/vocabulary.md"

#: The category taxonomy of decisions/vocabulary.md section 3: one code system
#: for both suites, and closed.  A new scenario names a category by its code or
#: its name and gets both, in meta and in the index (issue #157).
SCENARIO_CATEGORIES = (
    ("S1", "Basic semantic line changes"),
    ("S2", "Omission and deletion bugs"),
    ("S3", "Intermediate noise and history noise"),
    ("S4", "BFC-side noise and tangled commits"),
    ("S5", "Refactoring, move, and rename after BIC"),
    ("S6", "Multiple BICs, duplicate faults, and composite faults"),
    ("S7", "Context, message, and non-local evidence"),
    ("S8", "Non-source, configuration, test-only, and file-level edge cases"),
    ("G1", "Refactoring, move, rename, and semantic rewrite"),
    ("G2", "Clone, copy propagation, and origin-vs-direct BIC"),
    ("G3", "Multiple BICs, multiple BFCs, and partial fixes"),
    ("G4", "Branch, merge, cherry-pick, backport, and release branches"),
    ("G5", "Rebase-specific history rewriting"),
    ("G6", "Revert-specific reintroduction"),
    ("G7", "Issue, message, context, and non-local evidence"),
    ("G8", "Non-source, binary, generated, and scalability edge cases"),
    ("G9", "Evaluation policy variants"),
)

#: The statuses a new scenario starts in (decisions/vocabulary.md section 4).
#: ``retired`` describes a scenario whose directory has been removed.
NEW_SCENARIO_STATUSES = ("draft", "active")


class NewScenarioError(RuntimeError):
    pass


@dataclass(frozen=True)
class NewScenarioResult:
    scenario_id: str
    scenario_dir: Path
    scenario_path: Path
    readme_path: Path
    index_path: Path


def create_new_scenario(
    *,
    title: str,
    category: str,
    factors: list[str],
    tier: str,
    root: Path = DEFAULT_SCENARIOS_ROOT,
    slug: str | None = None,
    difficulty: str = "medium",
    status: str = "draft",
) -> NewScenarioResult:
    title = title.strip()
    category = category.strip()
    if not title:
        raise NewScenarioError("--title must not be empty")
    if not category:
        raise NewScenarioError("--category must not be empty")
    if difficulty not in SCENARIO_DIFFICULTIES:
        raise NewScenarioError(f"--difficulty must be one of {', '.join(SCENARIO_DIFFICULTIES)}, not '{difficulty}'")
    problem = vocabulary_problem(category=category, factors=factors, tier=tier, status=status, prefix="W")
    if problem:
        raise NewScenarioError(problem)
    category_code, category = resolve_category(category)

    root = root.resolve()
    index_path = root / "index.yml"
    index_data = _load_index(index_path)
    scenario_id = _next_scenario_id(root, index_data)
    scenario_slug = _slugify(slug or title) or scenario_id.lower()
    scenario_dir = root / scenario_id
    scenario_path = scenario_dir / "scenario.yml"
    readme_path = scenario_dir / "README.md"
    scenario_factors = list(factors)

    if scenario_dir.exists():
        raise NewScenarioError(f"Scenario directory already exists: {scenario_dir}")
    # Edit the index before writing anything, so that an index the entry
    # cannot be added to leaves the root as it was (issue #111).
    entry = index_entry(scenario_id=scenario_id, title=title, slug=scenario_slug, category_code=category_code,
                        category=category, factors=scenario_factors, difficulty=difficulty, status=status,
                        path=f"{root.name}/{scenario_id}/scenario.yml", readme=f"{root.name}/{scenario_id}/README.md")
    try:
        index_text = splice_index_entry(read_index_text(index_path, "scenarios:\n"), index_data, entry)
    except IndexSpliceError as exc:
        raise NewScenarioError(f"Cannot add {scenario_id} to {index_path}: {exc}. Nothing was written.") from exc

    root.mkdir(parents=True, exist_ok=True)
    scenario_dir.mkdir()
    scenario_path.write_text(
        _scenario_template(
            scenario_id=scenario_id,
            title=title,
            slug=scenario_slug,
            category=category,
            category_code=category_code,
            factors=scenario_factors,
            difficulty=difficulty,
            status=status,
            tier=tier,
        ),
        encoding="utf-8",
    )
    readme_path.write_text(_readme_template(scenario_path), encoding="utf-8")
    write_index_text(index_path, index_text)

    return NewScenarioResult(
        scenario_id=scenario_id,
        scenario_dir=scenario_dir,
        scenario_path=scenario_path,
        readme_path=readme_path,
        index_path=index_path,
    )


def index_entry(*, scenario_id: str, title: str, slug: str, category_code: str, category: str, factors: list[str],
                difficulty: str, status: str, path: str, readme: str) -> dict:
    """A new scenario's index entry: the keys of both indexes, in their order
    (``validator.INDEX_ENTRY_KEYS``, issue #200).  Both builders write it."""
    values = {"id": scenario_id, "title": title, "slug": slug, "category_code": category_code, "category": category,
              "factors": factors, "difficulty": difficulty, "status": status, "path": path, "readme": readme}
    return {key: values[key] for key in INDEX_ENTRY_KEYS}


def resolve_category(value: str) -> tuple[str, str] | None:
    """The ``(code, name)`` that a ``--category`` value names by its code or its name, or None."""
    for code, name in SCENARIO_CATEGORIES:
        if value in (code, name):
            return code, name
    return None


def vocabulary_problem(*, category: str, factors, tier: str, status: str, prefix: str) -> str | None:
    """What makes the skeleton options fall outside decisions/vocabulary.md, or None (issues #156, #157).

    Shared by both builders; ``prefix`` is the lint family (``W`` or ``GW``)
    whose factor codes the message cites.
    """
    if status not in NEW_SCENARIO_STATUSES:
        return (f"--status must be one of {', '.join(NEW_SCENARIO_STATUSES)}, not '{status}' "
                f"({VOCABULARY} section 4; a new scenario is not retired)")
    if tier not in SCENARIO_TIERS:
        return f"--tier must be one of {', '.join(SCENARIO_TIERS)}, not '{tier}' ({VOCABULARY} section 7)"
    if resolve_category(category) is None:
        known = "; ".join(f"{code} ({name})" for code, name in SCENARIO_CATEGORIES)
        return f"--category must be a category code or name from {VOCABULARY} section 3, not '{category}': {known}"
    return factor_problem(factors, prefix=prefix)


def factor_problem(factors, *, prefix: str) -> str | None:
    """The factor rules that ``--lint`` applies (``lint_factors``), plus whitespace, checked when the
    skeleton is made rather than after its commits are written (issue #157)."""
    rules = f"the factor rules of {VOCABULARY} section 1.1"
    factors = list(factors or [])
    if not factors:
        return f"at least one --factor is required ({rules})"
    problems = [f"factor '{factor}' is empty or contains whitespace; a factor is a hyphen-case tag "
                "such as multi-file-bfc" for factor in factors if factor.split() != [factor]]
    result = ValidationResult()
    lint_factors(factors, result, prefix=prefix)
    problems += [f"{finding.code}: {finding.message.rstrip('.')}" for finding in result.error_findings()]
    if problems:
        return f"--factor breaks {rules}: " + "; ".join(problems)
    return None


def _load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"scenarios": []}
    data, problem = load_index(index_path)         # a message that names index.yml (issue #158)
    if data is None:
        raise NewScenarioError(f"Cannot read {index_path}: {problem}")
    scenarios = data.get("scenarios")
    if scenarios is None:
        data["scenarios"] = []
    elif not isinstance(scenarios, list):
        raise NewScenarioError(f"{index_path} field 'scenarios' must be a list")
    return data


def _next_scenario_id(root: Path, index_data: dict) -> str:
    used_numbers: set[int] = set()
    for entry in index_data.get("scenarios", []):
        if isinstance(entry, dict):
            _collect_scenario_number(entry.get("id"), used_numbers)
    if root.exists():
        for child in root.iterdir():
            if child.is_dir():
                _collect_scenario_number(child.name, used_numbers)
    # A retired id is never issued again, even when it was the highest
    # (docs/retired-ids.md, issue #112).
    for retired in read_retired_ids(root):
        _collect_scenario_number(retired, used_numbers)
    number = max(used_numbers, default=0) + 1
    return f"SZZ-{number:04d}"


def _collect_scenario_number(value, used_numbers: set[int]) -> None:
    if not isinstance(value, str):
        return
    match = SCENARIO_ID_RE.match(value)
    if match:
        used_numbers.add(int(match.group(1)))


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _inline_list(values: list[str]) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(_quote(value) for value in values) + "]"


def _scenario_template(
    *,
    scenario_id: str,
    title: str,
    slug: str,
    category: str,
    category_code: str,
    factors: list[str],
    difficulty: str,
    status: str,
    tier: str,
) -> str:
    """A minimal history that ``validate --simulate --strict --lint`` accepts as it is (issue #156): the
    same three commits as the graph skeleton, so that the lints reach the factors and the messages
    before the author has written anything."""
    repository_name = f"{scenario_id}-{slug}"
    return f"""schema_version: "1.0"

meta:
  id: {_quote(scenario_id)}
  title: {_quote(title)}
  slug: {_quote(slug)}
  description: >
    TODO: Describe the bug pattern and why this scenario is useful.
  category: {_quote(category)}
  category_code: {_quote(category_code)}
  factors: {_inline_list(factors)}
  difficulty: {_quote(difficulty)}
  status: {_quote(status)}
{tier_lines(tier)}
repository:
  name: {_quote(repository_name)}
  default_branch: "main"
  language: "java"
  build_system: "none"
  source_root: "src/main/java"

# TODO: Replace this minimal history with the commits, bugs, and checks of this scenario.
commits:
  - id: "c0"
    message: "Initial implementation"
    role: "initial"
    operations:
      - type: "write_file"
        path: "src/main/java/example/Range.java"
        content: |
          package example;

          public class Range {{
              public boolean contains(int value, int min, int max) {{
                  return value >= min && value <= max;
              }}
          }}

  - id: "c1"
    message: "Narrow the range check"
    role: "bug_introducing"
    operations:
      - type: "replace"
        path: "src/main/java/example/Range.java"
        old: "return value >= min && value <= max;"
        new: "return value > min && value < max;"

  - id: "c2"
    message: "Fix bug"
    role: "bug_fixing"
    operations:
      - type: "replace"
        path: "src/main/java/example/Range.java"
        old: "return value > min && value < max;"
        new: "return value >= min && value <= max;"

bugs:
  - id: "B001"
    title: "TODO: Bug title"
    bug_fixing_commit: "c2"
    bug_introducing_commits:
      - "c1"
    fault:
      commit: "c1"
      file: "src/main/java/example/Range.java"
      statement: "return value > min && value < max;"
      change_type: "line_modification"
    fix:
      commit: "c2"
      file: "src/main/java/example/Range.java"
      statement: "return value >= min && value <= max;"
      fix_type: "line_modification"
    expected_szz:
      commit_level:
        true_positives:
          - "c1"
        false_positives_allowed: []
      line_level:
        available: true
        faulty_statements:
          - "return value > min && value < max;"

checks:
  - type: "git_history_contains"
    commits: ["c0", "c1", "c2"]
"""


def tier_lines(tier: str) -> str:
    """``meta.tier``, and for ``discriminating`` the ``meta.defeats`` the tier implies (W462 / GW462)."""
    if tier != "discriminating":
        return f"  tier: {_quote(tier)}\n"
    return (f"  tier: {_quote(tier)}\n"
            "  # TODO: a discriminating scenario needs an oracle of at least two commits\n"
            f"  # ({VOCABULARY} section 7).\n"
            f"  defeats: {_inline_list(list(DEFEATABLE_FAMILIES))}\n")


def _readme_template(scenario_path: Path) -> str:
    """The generated header rendered from the skeleton, then the sections a
    scenario README carries by hand (``docs/scenario-readme.md``)."""
    from .readme import render_header, suite_of

    data, _ = load_yaml(scenario_path)
    return render_header(data or {}, suite_of(scenario_path)) + """
## Purpose

TODO: What this scenario checks, and what a tool has to get right to pass it.

## Commit structure

- `c0`: TODO
- `c1`: TODO (BIC)
- `c2`: TODO (BFC)

## Expected behavior

TODO: The expected BIC and BFC, and the evidence (behaviour at each commit, blame of the deleted lines) that the oracle is right.
"""
