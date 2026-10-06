from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

from .index_splice import IndexSpliceError, read_index_text, splice_index_entry, write_index_text
from .retired_ids import read_retired_ids
from .scenario import load_yaml
from .validator import SCENARIO_DIFFICULTIES

DEFAULT_GRAPH_SCENARIOS_ROOT = Path("advanced-scenarios")
GRAPH_SCENARIO_ID_RE = re.compile(r"^SZZG-(\d+)$")


class NewGraphScenarioError(RuntimeError):
    pass


@dataclass(frozen=True)
class NewGraphScenarioResult:
    scenario_id: str
    scenario_dir: Path
    scenario_path: Path
    readme_path: Path
    index_path: Path


def create_new_graph_scenario(
    *,
    title: str,
    category: str,
    root: Path = DEFAULT_GRAPH_SCENARIOS_ROOT,
    slug: str | None = None,
    factors: list[str] | None = None,
    difficulty: str = "medium",
    status: str = "draft",
) -> NewGraphScenarioResult:
    title = title.strip()
    category = category.strip()
    if not title:
        raise NewGraphScenarioError("--title must not be empty")
    if not category:
        raise NewGraphScenarioError("--category must not be empty")
    if difficulty not in SCENARIO_DIFFICULTIES:
        # ``advanced`` was the graph suite's placeholder until 2026-09-22; a new
        # scenario is graded like any other (decisions/vocabulary.md section 4).
        raise NewGraphScenarioError(f"--difficulty must be one of {', '.join(SCENARIO_DIFFICULTIES)}, not '{difficulty}'")

    root = root.resolve()
    index_path = root / "index.yml"
    index_data = _load_index(index_path)
    scenario_id = _next_graph_scenario_id(root, index_data)
    scenario_slug = _slugify(slug or title) or scenario_id.lower()
    scenario_dir = root / scenario_id
    scenario_path = scenario_dir / "scenario.graph.yml"
    readme_path = scenario_dir / "README.md"
    scenario_factors = factors or []

    if scenario_dir.exists():
        raise NewGraphScenarioError(f"Graph scenario directory already exists: {scenario_dir}")
    # Edit the index before writing anything, so that an index the entry
    # cannot be added to leaves the root as it was (issue #111).  The keys and
    # their order are the graph index's own: it carries no slug or difficulty.
    entry = {
        "id": scenario_id,
        "title": title,
        "category": category,
        "path": f"{root.name}/{scenario_id}/scenario.graph.yml",
        "readme": f"{root.name}/{scenario_id}/README.md",
        "status": status,
        "factors": scenario_factors,
    }
    try:
        index_text = splice_index_entry(
            read_index_text(index_path, 'schema_version: "graph-index-0.1-draft"\nscenarios:\n'), index_data, entry)
    except IndexSpliceError as exc:
        raise NewGraphScenarioError(f"Cannot add {scenario_id} to {index_path}: {exc}. Nothing was written.") from exc

    root.mkdir(parents=True, exist_ok=True)
    scenario_dir.mkdir()
    scenario_path.write_text(
        _graph_scenario_template(
            scenario_id=scenario_id,
            title=title,
            slug=scenario_slug,
            category=category,
            factors=scenario_factors,
            difficulty=difficulty,
            status=status,
        ),
        encoding="utf-8",
    )
    readme_path.write_text(_readme_template(scenario_path), encoding="utf-8")
    write_index_text(index_path, index_text)

    return NewGraphScenarioResult(
        scenario_id=scenario_id,
        scenario_dir=scenario_dir,
        scenario_path=scenario_path,
        readme_path=readme_path,
        index_path=index_path,
    )


def _load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"schema_version": "graph-index-0.1-draft", "scenarios": []}
    data, result = load_yaml(index_path)
    if result.has_errors() or data is None:
        details = "; ".join(f.message for f in result.findings) or "invalid index.yml"
        raise NewGraphScenarioError(f"Cannot read {index_path}: {details}")
    scenarios = data.get("scenarios")
    if scenarios is None:
        data["scenarios"] = []
    elif not isinstance(scenarios, list):
        raise NewGraphScenarioError(f"{index_path} field 'scenarios' must be a list")
    return data


def _next_graph_scenario_id(root: Path, index_data: dict) -> str:
    used_numbers: set[int] = set()
    for entry in index_data.get("scenarios", []):
        if isinstance(entry, dict):
            _collect_graph_scenario_number(entry.get("id"), used_numbers)
    if root.exists():
        for child in root.iterdir():
            if child.is_dir():
                _collect_graph_scenario_number(child.name, used_numbers)
    # A retired id is never issued again, even when it was the highest
    # (docs/retired-ids.md, issue #112).
    for retired in read_retired_ids(root):
        _collect_graph_scenario_number(retired, used_numbers)
    number = max(used_numbers, default=0) + 1
    return f"SZZG-{number:04d}"


def _collect_graph_scenario_number(value, used_numbers: set[int]) -> None:
    if not isinstance(value, str):
        return
    match = GRAPH_SCENARIO_ID_RE.match(value)
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


def _graph_scenario_template(
    *,
    scenario_id: str,
    title: str,
    slug: str,
    category: str,
    factors: list[str],
    difficulty: str,
    status: str,
) -> str:
    repository_name = f"{scenario_id}-{slug}"
    return f'''schema_version: "graph-0.1-draft"

meta:
  id: {_quote(scenario_id)}
  title: {_quote(title)}
  slug: {_quote(slug)}
  description: >
    TODO: Describe the graph scenario and why it is useful for SZZ evaluation.
  category: {_quote(category)}
  factors: {_inline_list(factors)}
  difficulty: {_quote(difficulty)}
  status: {_quote(status)}
  related_simple_scenarios: []

repository:
  name: {_quote(repository_name)}
  default_branch: "main"
  language: "java"
  build_system: "none"
  source_root: "src/main/java"

graph:
  model: "commit_dag"
  default_branch: "main"
  history_summary: >
    TODO: Summarize the intended commit graph.

commits:
  - id: "c0"
    branch: "main"
    parents: []
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
    branch: "main"
    parents: ["c0"]
    message: "Introduce bug"
    role: "bug_introducing"
    operations:
      - type: "replace"
        path: "src/main/java/example/Range.java"
        old: "return value >= min && value <= max;"
        new: "return value > min && value < max;"

  - id: "c2"
    branch: "main"
    parents: ["c1"]
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
    bug_introducing_commits:
      - commit: "c1"
        role: "direct"
    bug_fixing_commits:
      - commit: "c2"
        role: "complete_fix"
    faults:
      - id: "F001"
        commit: "c1"
        file: "src/main/java/example/Range.java"
        statement: "return value > min && value < max;"
        change_type: "line_modification"
    fixes:
      - id: "X001"
        commit: "c2"
        file: "src/main/java/example/Range.java"
        statement: "return value >= min && value <= max;"
        fix_type: "line_modification"

expected_szz:
  commit_level:
    evaluation_policy: "exact_set"
    required:
      - "c1"

graph_extensions: []
evaluation_points: []
notes:
  - "TODO: Add notes about why this needs scenario.graph.yml."
'''


def _readme_template(scenario_path: Path) -> str:
    """The generated header rendered from the skeleton, then the sections a
    graph scenario README carries by hand (``docs/scenario-readme.md``).  The
    header's ``graph features`` row states which graph-only features the
    scenario uses, so the README does not repeat that."""
    from .readme import render_header, suite_of

    data, _ = load_yaml(scenario_path)
    return render_header(data or {}, suite_of(scenario_path)) + """
## Purpose

TODO: What this scenario checks, and what a tool has to get right to pass it.

## Expected history

```text
c0: create initial state (write_file TODO)
c1: introduce bug (replace TODO)
c2: fix bug (replace TODO)
```

## Expected BIC / BFC

TODO: The expected BICs and BFCs, the policy, and the evidence (behaviour at each commit, blame of the deleted lines) that the oracle is right.
"""
