from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .cleaner import CleanError, DEFAULT_CLEAN_ROOT, clean_generated_outputs
from .generator import GenerationError, generate_repository
from .graph_generator import GraphGenerationError, generate_graph_repository
from .scenario_builder import DEFAULT_SCENARIOS_ROOT, NewScenarioError, create_new_scenario
from .graph_scenario_builder import DEFAULT_GRAPH_SCENARIOS_ROOT, NewGraphScenarioError, create_new_graph_scenario
from .validator import validate_scenario_file
from .graph_validator import validate_graph_scenario_file
from .verifier import verify_generated_repo
from .graph_verifier import verify_graph_generated_repo

def print_result(result, *, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    for finding in result.findings:
        location = f" ({finding.location})" if finding.location else ""
        print(f"[{finding.severity}] {finding.code}: {finding.message}{location}")
    print(f"Summary: {result.error_count()} error(s), {result.warning_count()} warning(s), {result.info_count()} info item(s)")

def cmd_validate(args) -> int:
    _, result, _ = validate_scenario_file(Path(args.scenario), simulate=args.simulate)
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_generate(args) -> int:
    try:
        commit_map, verify_result = generate_repository(Path(args.scenario), Path(args.out), force=args.force, verify=not args.no_verify)
    except GenerationError as exc:
        print(f"[ERROR] GENERATION_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"Generated repository under: {Path(args.out).resolve()}")
    print(f"Created {len(commit_map)} commit(s).")
    if verify_result is not None:
        print_result(verify_result, json_output=False)
        return 1 if verify_result.has_errors() else 0
    return 0

def cmd_verify(args) -> int:
    result = verify_generated_repo(Path(args.repo), Path(args.scenario), Path(args.commit_map) if args.commit_map else None)
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_validate_graph(args) -> int:
    _, result = validate_graph_scenario_file(Path(args.scenario), strict_paths=args.strict_paths, simulate=args.simulate)
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_generate_graph(args) -> int:
    try:
        commit_map, verify_result = generate_graph_repository(Path(args.scenario), Path(args.out), force=args.force, verify=not args.no_verify)
    except GraphGenerationError as exc:
        print(f"[ERROR] GRAPH_GENERATION_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"Generated graph repository under: {Path(args.out).resolve()}")
    print(f"Created {len(commit_map)} graph commit(s).")
    if verify_result is not None:
        print_result(verify_result, json_output=False)
        return 1 if verify_result.has_errors() else 0
    return 0

def cmd_verify_graph(args) -> int:
    result = verify_graph_generated_repo(
        Path(args.repo),
        Path(args.scenario),
        Path(args.commit_map) if args.commit_map else None,
        Path(args.graph_map) if args.graph_map else None,
    )
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_new_graph_scenario(args) -> int:
    try:
        result = create_new_graph_scenario(
            title=args.title,
            category=args.category,
            root=Path(args.root),
            slug=args.slug,
            factors=args.factor,
            difficulty=args.difficulty,
            status=args.status,
        )
    except NewGraphScenarioError as exc:
        print(f"[ERROR] NEW_GRAPH_SCENARIO_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"Created {_display_path(result.scenario_dir)}/")
    print(f"Updated {_display_path(result.index_path)}")
    return 0

def cmd_clean(args) -> int:
    root = Path(args.root)
    try:
        outputs = clean_generated_outputs(root, dry_run=args.dry_run)
    except CleanError as exc:
        print(f"[ERROR] CLEAN_FAILED: {exc}", file=sys.stderr)
        return 1
    root_display = root.resolve()
    if not outputs:
        print(f"No generated repositories found under: {root_display}")
        return 0
    verb = "Would remove" if args.dry_run else "Removed"
    for output in outputs:
        print(f"{verb}: {output}")
    suffix = "found" if args.dry_run else "removed"
    print(f"Summary: {len(outputs)} generated output(s) {suffix}.")
    return 0

def cmd_new_scenario(args) -> int:
    try:
        result = create_new_scenario(
            title=args.title,
            category=args.category,
            root=Path(args.root),
            slug=args.slug,
            factors=args.factor,
            difficulty=args.difficulty,
            status=args.status,
        )
    except NewScenarioError as exc:
        print(f"[ERROR] NEW_SCENARIO_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"Created {_display_path(result.scenario_dir)}/")
    print(f"Updated {_display_path(result.index_path)}")
    return 0

def _display_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="szzbench")
    sub = parser.add_subparsers(dest="command", required=True)
    p_validate = sub.add_parser("validate", help="Validate scenario.yml")
    p_validate.add_argument("scenario")
    p_validate.add_argument("--simulate", action="store_true", help="Also simulate operations in memory")
    p_validate.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    p_validate.add_argument("--json", action="store_true", help="Print JSON output")
    p_validate.set_defaults(func=cmd_validate)
    p_generate = sub.add_parser("generate", help="Generate a synthetic Git repository from scenario.yml")
    p_generate.add_argument("scenario")
    p_generate.add_argument("--out", required=True, help="Output directory containing repo/ and metadata/")
    p_generate.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    p_generate.add_argument("--no-verify", action="store_true", help="Skip post-generation verification")
    p_generate.set_defaults(func=cmd_generate)
    p_verify = sub.add_parser("verify", help="Verify a generated repository against scenario.yml")
    p_verify.add_argument("repo")
    p_verify.add_argument("--scenario", required=True)
    p_verify.add_argument("--commit-map", help="Path to commit-map.json")
    p_verify.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    p_verify.add_argument("--json", action="store_true", help="Print JSON output")
    p_verify.set_defaults(func=cmd_verify)
    p_validate_graph = sub.add_parser("validate-graph", help="Validate scenario.graph.yml")
    p_validate_graph.add_argument("scenario")
    p_validate_graph.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    p_validate_graph.add_argument("--strict-paths", action="store_true", help="Run additional strict path/entity-shape checks")
    p_validate_graph.add_argument("--simulate", action="store_true", help="Also simulate graph operations in memory")
    p_validate_graph.add_argument("--json", action="store_true", help="Print JSON output")
    p_validate_graph.set_defaults(func=cmd_validate_graph)

    p_generate_graph = sub.add_parser("generate-graph", help="Generate a synthetic Git repository from scenario.graph.yml")
    p_generate_graph.add_argument("scenario")
    p_generate_graph.add_argument("--out", required=True, help="Output directory containing repo/ and metadata/")
    p_generate_graph.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    p_generate_graph.add_argument("--no-verify", action="store_true", help="Skip post-generation graph verification")
    p_generate_graph.set_defaults(func=cmd_generate_graph)

    p_verify_graph = sub.add_parser("verify-graph", help="Verify a generated repository against scenario.graph.yml")
    p_verify_graph.add_argument("repo")
    p_verify_graph.add_argument("--scenario", required=True)
    p_verify_graph.add_argument("--commit-map", help="Path to commit-map.json")
    p_verify_graph.add_argument("--graph-map", help="Path to graph-map.json")
    p_verify_graph.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    p_verify_graph.add_argument("--json", action="store_true", help="Print JSON output")
    p_verify_graph.set_defaults(func=cmd_verify_graph)

    p_new_graph = sub.add_parser("new-graph-scenario", help="Create a new graph scenario skeleton")
    p_new_graph.add_argument("--title", required=True, help="Graph scenario title")
    p_new_graph.add_argument("--category", required=True, help="Graph scenario category")
    p_new_graph.add_argument("--root", default=str(DEFAULT_GRAPH_SCENARIOS_ROOT), help="Graph scenario root directory")
    p_new_graph.add_argument("--slug", help="Override the generated slug")
    p_new_graph.add_argument("--factor", action="append", default=[], help="Graph scenario factor; can be repeated")
    p_new_graph.add_argument("--difficulty", default="advanced", help="Graph scenario difficulty")
    p_new_graph.add_argument("--status", default="draft", help="Graph scenario status")
    p_new_graph.set_defaults(func=cmd_new_graph_scenario)

    p_clean = sub.add_parser("clean", help="Remove generated repositories")
    p_clean.add_argument("--root", default=str(DEFAULT_CLEAN_ROOT), help="Root directory to scan for generated outputs")
    p_clean.add_argument("--dry-run", action="store_true", help="Show generated outputs without removing them")
    p_clean.set_defaults(func=cmd_clean)
    p_new = sub.add_parser("new-scenario", help="Create a new scenario skeleton")
    p_new.add_argument("--title", required=True, help="Scenario title")
    p_new.add_argument("--category", required=True, help="Scenario category")
    p_new.add_argument("--root", default=str(DEFAULT_SCENARIOS_ROOT), help="Scenario root directory")
    p_new.add_argument("--slug", help="Override the generated slug")
    p_new.add_argument("--factor", action="append", default=[], help="Scenario factor; can be repeated")
    p_new.add_argument("--difficulty", default="medium", help="Scenario difficulty")
    p_new.add_argument("--status", default="draft", help="Scenario status")
    p_new.set_defaults(func=cmd_new_scenario)
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
