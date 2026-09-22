from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

from .scenario import load_yaml
from .validator import SCENARIO_DIFFICULTIES

DEFAULT_SCENARIOS_ROOT = Path("scenarios")
SCENARIO_ID_RE = re.compile(r"^SZZ-(\d+)$")


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
    root: Path = DEFAULT_SCENARIOS_ROOT,
    slug: str | None = None,
    factors: list[str] | None = None,
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

    root = root.resolve()
    index_path = root / "index.yml"
    index_data = _load_index(index_path)
    scenario_id = _next_scenario_id(root, index_data)
    scenario_slug = _slugify(slug or title) or scenario_id.lower()
    scenario_dir = root / scenario_id
    scenario_path = scenario_dir / "scenario.yml"
    readme_path = scenario_dir / "README.md"
    scenario_factors = factors or []

    if scenario_dir.exists():
        raise NewScenarioError(f"Scenario directory already exists: {scenario_dir}")

    root.mkdir(parents=True, exist_ok=True)
    scenario_dir.mkdir()
    scenario_path.write_text(
        _scenario_template(
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
    _append_index_entry(
        index_path,
        scenario_id=scenario_id,
        title=title,
        slug=scenario_slug,
        category=category,
        factors=scenario_factors,
        difficulty=difficulty,
        status=status,
        scenario_path=scenario_path,
    )

    return NewScenarioResult(
        scenario_id=scenario_id,
        scenario_dir=scenario_dir,
        scenario_path=scenario_path,
        readme_path=readme_path,
        index_path=index_path,
    )


def _load_index(index_path: Path) -> dict:
    if not index_path.exists():
        return {"scenarios": []}
    data, result = load_yaml(index_path)
    if result.has_errors() or data is None:
        details = "; ".join(f.message for f in result.findings) or "invalid index.yml"
        raise NewScenarioError(f"Cannot read {index_path}: {details}")
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
    factors: list[str],
    difficulty: str,
    status: str,
) -> str:
    repository_name = f"{scenario_id}-{slug}"
    return f"""schema_version: "1.0"

meta:
  id: {_quote(scenario_id)}
  title: {_quote(title)}
  slug: {_quote(slug)}
  description: >
    TODO: Describe the bug pattern and why this scenario is useful.
  category: {_quote(category)}
  factors: {_inline_list(factors)}
  difficulty: {_quote(difficulty)}
  status: {_quote(status)}

repository:
  name: {_quote(repository_name)}
  default_branch: "main"
  language: "TODO"
  build_system: "none"
  source_root: "."

# TODO: Replace these empty lists with the commits, bugs, and checks for this scenario.
commits: []

bugs: []

checks: []
"""


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


def _append_index_entry(
    index_path: Path,
    *,
    scenario_id: str,
    title: str,
    slug: str,
    category: str,
    factors: list[str],
    difficulty: str,
    status: str,
    scenario_path: Path,
) -> None:
    if index_path.exists():
        text = index_path.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
    else:
        text = "scenarios:\n"
    relative_path = _index_path(scenario_path)
    entry = f"""
  - id: {_quote(scenario_id)}
    title: {_quote(title)}
    slug: {_quote(slug)}
    category: {_quote(category)}
    factors: {_inline_list(factors)}
    difficulty: {_quote(difficulty)}
    status: {_quote(status)}
    path: {_quote(relative_path)}
"""
    index_path.write_text(text + entry, encoding="utf-8")


def _index_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()
