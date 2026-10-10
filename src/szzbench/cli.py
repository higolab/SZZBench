from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .bulk_generator import (
    DEFAULT_ADVANCED_SCENARIOS_ROOT,
    DEFAULT_GENERATED_INPUT_REPOS_ROOT,
    GenerateAllRepositoriesError,
    generate_all_repositories,
)
from .cleaner import (
    CleanError,
    DEFAULT_CLEAN_ROOT,
    find_generated_outputs,
    is_default_clean_root,
    remove_generated_outputs,
)
from .generator import GenerationError, generate_repository
from .graph_generator import GraphGenerationError, generate_graph_repository
from .scenario import load_yaml
from .scenario_builder import DEFAULT_SCENARIOS_ROOT, NewScenarioError, create_new_scenario
from .graph_scenario_builder import DEFAULT_GRAPH_SCENARIOS_ROOT, NewGraphScenarioError, create_new_graph_scenario
from .validator import SCENARIO_DIFFICULTIES, graph_scenario_guard, validate_scenario_file, validate_scenario_indexes
from .graph_validator import validate_graph_scenario_file
from .verifier import verify_generated_repo
from .graph_verifier import verify_graph_generated_repo
from .baselines import FAMILIES as BASELINE_FAMILIES, format_report as format_baselines, run_baselines
from .coverage import format_report as format_coverage, run_coverage
from .readme import format_readme_report, resolve_targets, run_readme, scenario_files
from .evaluator import _format_fix_shape_counts, evaluate_predictions

def print_result(result, *, json_output: bool = False, file=None) -> None:
    if json_output:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), file=file)
        return
    for finding in result.findings:
        print(finding.format(), file=file)
    print(f"Summary: {result.error_count()} error(s), {result.warning_count()} warning(s), {result.info_count()} info item(s)",
          file=file)

def cmd_validate(args) -> int:
    _, result, _ = validate_scenario_file(Path(args.scenario), simulate=args.simulate, lint=args.lint)
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_generate(args) -> int:
    # Before generate_repository, whose validation would only say "run validate"
    # for a graph scenario rather than name generate-graph (issue #119).
    scenario, _ = load_yaml(Path(args.scenario))
    if scenario is not None:
        guard = graph_scenario_guard(scenario, Path(args.scenario), "generate")
        if guard.has_errors():
            if args.json:
                error = "; ".join(f"{finding.code}: {finding.message}" for finding in guard.error_findings())
                _print_json(_generation_document(args, "classic", error=error))
                return 1
            for finding in guard.findings:
                print(f"[ERROR] {finding.code}: {finding.message}", file=sys.stderr)
            return 1
    try:
        commit_map, verify_result = generate_repository(Path(args.scenario), Path(args.out), force=args.force, verify=not args.no_verify)
    except GenerationError as exc:
        return _report_failed_generation(args, "classic", "GENERATION_FAILED", exc)
    return _report_generation(args, "classic", commit_map, verify_result, "Generated repository under", "commit(s)")

def _report_generation(args, kind: str, commit_map: dict, verify_result, generated: str, commits: str) -> int:
    """What ``generate`` and ``generate-graph`` print for a generation that succeeded, and their exit code.

    The verification's warnings were printed and left the exit code 0; with
    ``--strict`` they fail it, as ``verify --strict`` does (issue #169).
    """
    if args.json:
        _print_json(_generation_document(args, kind, commit_map=commit_map, verify_result=verify_result))
    else:
        print(f"{generated}: {Path(args.out).resolve()}")
        print(f"Created {len(commit_map)} {commits}.")
        if verify_result is not None:
            print_result(verify_result)
    if verify_result is None:
        return 0
    if verify_result.has_errors():
        return 1
    return 1 if args.strict and verify_result.warning_count() > 0 else 0

def _report_failed_generation(args, kind: str, code: str, exc) -> int:
    if args.json:
        _print_json(_generation_document(args, kind, verify_result=exc.verify_result, error=str(exc)))
        return 1
    print(f"[ERROR] {code}: {exc}", file=sys.stderr)
    if exc.verify_result is not None:       # why verification failed: it was in verify-result.json only (#163)
        print_result(exc.verify_result, file=sys.stderr)
    return 1

def _generation_document(args, kind: str, *, commit_map: dict | None = None, verify_result=None,
                         error: str | None = None) -> dict:
    """What ``generate --json`` and ``generate-graph --json`` print: the keys of an item of
    ``generate-all-repos --json`` that apply to one generation (issue #169)."""
    return {
        "kind": kind,
        "scenario": str(Path(args.scenario).resolve()),
        "output_dir": str(Path(args.out).resolve()),
        "status": "failed" if error is not None else "generated",
        "commit_count": len(commit_map) if commit_map is not None else 0,
        "error": error,
        "verification": verify_result.to_dict() if verify_result is not None else None,
    }

def _print_json(document: dict) -> None:
    print(json.dumps(document, indent=2, ensure_ascii=False))

def cmd_verify(args) -> int:
    result = verify_generated_repo(Path(args.repo), Path(args.scenario), Path(args.commit_map) if args.commit_map else None)
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_validate_graph(args) -> int:
    _, result = validate_graph_scenario_file(Path(args.scenario), strict_paths=args.strict_paths, simulate=args.simulate, lint=args.lint)
    print_result(result, json_output=args.json)
    if result.has_errors():
        return 1
    if args.strict and result.warning_count() > 0:
        return 1
    return 0

def cmd_validate_index(args) -> int:
    result = validate_scenario_indexes(Path(args.scenarios_root), Path(args.advanced_scenarios_root))
    print_result(result, json_output=args.json)
    return 1 if result.has_errors() else 0

def cmd_generate_graph(args) -> int:
    try:
        commit_map, verify_result = generate_graph_repository(Path(args.scenario), Path(args.out), force=args.force, verify=not args.no_verify)
    except GraphGenerationError as exc:
        return _report_failed_generation(args, "graph", "GRAPH_GENERATION_FAILED", exc)
    return _report_generation(args, "graph", commit_map, verify_result, "Generated graph repository under",
                              "graph commit(s)")

def cmd_generate_all_repos(args) -> int:
    try:
        result = generate_all_repositories(
            scenarios_root=Path(args.scenarios_root),
            advanced_scenarios_root=Path(args.advanced_scenarios_root),
            output_root=Path(args.out_root),
            overwrite=args.overwrite,
            verify=not args.no_verify,
        )
    except GenerateAllRepositoriesError as exc:
        print(f"[ERROR] GENERATE_ALL_REPOS_FAILED: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(result.to_dict())
    else:
        _print_generate_all_repos(result)
    if result.failed_count:
        return 1
    # a verification warning was written to verify-result.json and never shown, and
    # nothing could fail the run on it (issue #169)
    return 1 if args.strict and result.warned_count else 0

def _print_generate_all_repos(result) -> None:
    for item in result.items:
        output = _display_path(item.output_dir)
        if item.status == "skipped":
            print(f"Skipped [{item.kind}] {item.scenario_id}: {output} is up to date.")
        elif item.status == "generated" and item.stale_reason is not None:
            print(f"Regenerated [{item.kind}] {item.scenario_id}: {output} ({item.commit_count} commit(s)); "
                  f"the old output was stale: {item.stale_reason}.")
        elif item.status == "generated":
            verb = "Overwrote" if item.overwritten else "Generated"
            print(f"{verb} [{item.kind}] {item.scenario_id}: {output} ({item.commit_count} commit(s)).")
        else:
            print(f"Failed [{item.kind}] {item.scenario_id}: {output}: {item.error}", file=sys.stderr)
            for finding in item.verification_errors:    # why verification failed (issue #163)
                print(f"  {finding.format()}", file=sys.stderr)
            if item.traceback:                  # not a generation error: say where it came from (#162)
                print("  " + item.traceback.rstrip().replace("\n", "\n  "), file=sys.stderr)
        if item.status != "failed" and item.verification is not None:
            # what `generate` prints, named by the scenario since stdout and stderr can be read apart (#169)
            for finding in item.verification.findings:
                if finding.severity == "WARNING":
                    print(f"{item.scenario_id}: {finding.format()}", file=sys.stderr)

    print("Summary:")
    print(f"  Total:       {result.total_count}")
    print(f"  Generated:   {result.generated_count}")
    print(f"  Skipped:     {result.skipped_count}")
    print(f"  Overwritten: {result.overwritten_count}")
    print(f"  Regenerated: {result.regenerated_count} (stale outputs, without --overwrite)")
    print(f"  Failed:      {result.failed_count}")
    print(f"  Warned:      {result.warned_count} (verification warnings; --strict fails on them)")
    if result.orphans:
        print(f"  Orphaned:    {len(result.orphans)}")
        for orphan in result.orphans:
            print(f"[WARNING] {_display_path(orphan)} has no scenario; it was probably retired "
                  f"(see docs/retired-ids.md). Remove it, or run `szzbench clean` and regenerate.", file=sys.stderr)

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

def _prepare_out_dir(out: str | None, code: str) -> bool:
    """Create the ``--out`` directory before the command does its work (issue #143).

    The commands created it only to write their reports, so a file of that name
    ended them, a whole ``baselines`` run included, in a FileExistsError traceback.
    """
    if out is None:
        return True
    path = Path(out)
    if path.exists() and not path.is_dir():
        print(f"[ERROR] {code}: --out must be a directory, and {out} is not one.", file=sys.stderr)
        return False
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        reason = exc.strerror or str(exc)
        if exc.filename is not None and str(exc.filename) != str(path):     # a parent it could not create
            reason = f"{exc.filename}: {reason}"
        print(f"[ERROR] {code}: cannot create the --out directory {out} ({reason}).", file=sys.stderr)
        return False
    return True

def cmd_baselines(args) -> int:
    if not _prepare_out_dir(args.out, "BASELINES_FAILED"):
        return 1
    report = run_baselines(
        generated_root=Path(args.generated_root),
        scenarios_root=Path(args.scenarios_root),
        advanced_scenarios_root=Path(args.advanced_scenarios_root),
        variant=args.variant,
        families=args.family or BASELINE_FAMILIES,
    )
    if not report["scenario_count"]:
        for error in report["errors"]:          # why an output was not scored, e.g. it is stale (#93)
            print(f"[ERROR] {error}", file=sys.stderr)
        print("[ERROR] BASELINES_FAILED: no generated repository could be scored; run generate-all-repos first.",
              file=sys.stderr)
        return 1
    text = format_baselines(report)
    if args.out:
        out_dir = Path(args.out)
        (out_dir / "baselines.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out_dir / "baselines.md").write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else text)
    return 1 if report["errors"] else 0


def cmd_coverage(args) -> int:
    if not _prepare_out_dir(args.out, "COVERAGE_FAILED"):
        return 1
    report = run_coverage(
        generated_root=Path(args.generated_root),
        scenarios_root=Path(args.scenarios_root),
        advanced_scenarios_root=Path(args.advanced_scenarios_root),
        variant=args.variant,
    )
    if not report["scenario_count"]:
        for error in report["errors"]:          # why an output was not scored, e.g. it is stale (#93)
            print(f"[ERROR] {error}", file=sys.stderr)
        print("[ERROR] COVERAGE_FAILED: no generated repository could be scored; run generate-all-repos first.",
              file=sys.stderr)
        return 1
    text = format_coverage(report)
    if args.out:
        out_dir = Path(args.out)
        (out_dir / "coverage.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out_dir / "coverage.md").write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else text)
    return 1 if report["errors"] else 0


def cmd_readme(args) -> int:
    files = resolve_targets(args.scenarios) if args.scenarios else scenario_files(
        Path(args.scenarios_root), Path(args.advanced_scenarios_root))
    report = run_readme(files, write=args.write)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else format_readme_report(report, write=args.write))
    if report["errors"]:
        return 1
    if args.write:
        # --write checks what it wrote: a README still stale afterwards fails the run (issue #184)
        return 1 if report["unresolved"] else 0
    return 1 if report["stale"] else 0

def cmd_evaluate(args) -> int:
    if not args.predictions and not args.include_generated:
        print("[ERROR] EVALUATE_FAILED: --predictions is required unless --include-generated is used.", file=sys.stderr)
        return 1
    generated_root = Path(args.generated_root)
    if args.include_generated and not generated_root.is_dir():
        # the walk over it found nothing, and nothing said so (issue #141)
        problem = "is not a directory" if generated_root.exists() else "does not exist"
        print(f"[ERROR] EVALUATE_FAILED: --generated-root {args.generated_root} {problem}; pass the directory "
              "generate-all-repos wrote, or run it first.", file=sys.stderr)
        return 1
    if not _prepare_out_dir(args.out, "EVALUATE_FAILED"):
        return 1
    report = evaluate_predictions(
        Path(args.predictions) if args.predictions else None,
        generated_root=generated_root,
        scenarios_root=Path(args.scenarios_root),
        advanced_scenarios_root=Path(args.advanced_scenarios_root),
        variant=args.variant,
        include_generated=args.include_generated,
        evaluation_variant=args.evaluation_variant,
        reference_format=args.reference_format,
    )
    if not report.scenarios:
        # An empty predictions file or a root without outputs scored nothing, and exited 0 even
        # with --fail-on-non-pass (issue #141).  An error of the report, so that the --out
        # reports agree with the exit code.
        report.errors.append(_nothing_scored_message(args, report.errors))
    if args.out:
        out_dir = Path(args.out)
        (out_dir / "evaluation-results.json").write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (out_dir / "evaluation-results.md").write_text(report.to_markdown(), encoding="utf-8")
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        _print_evaluation_summary(report.summary())
        if args.out:
            print(f"Wrote: {_display_path(Path(args.out) / 'evaluation-results.json')}")
            print(f"Wrote: {_display_path(Path(args.out) / 'evaluation-results.md')}")
        for error in report.errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        for warning in report.warnings:
            print(f"[WARNING] {warning}", file=sys.stderr)
        for note in report.info:
            print(f"[INFO] {note}", file=sys.stderr)
    if report.errors:
        return 1
    if args.fail_on_non_pass and report.summary()["fail"] > 0:
        return 1
    return 0

def _nothing_scored_message(args, errors: list[str]) -> str:
    """Why ``evaluate`` scored no scenario (issue #141).

    An unreadable file, a scenario that does not exist and a stale output each
    have their error already.  Without one, the predictions file holds no
    record, and ``--include-generated`` found no output of a scenario.
    """
    if errors:
        return "EVALUATE_FAILED: no scenario was scored; the other errors say why."
    causes = []
    if args.predictions:
        causes.append(f"{args.predictions} holds no prediction record")
    if args.include_generated:
        causes.append(f"--generated-root {args.generated_root} holds no <scenario-id>/{args.variant} output of a "
                      "known scenario; run generate-all-repos first")
    return "EVALUATE_FAILED: no scenario was scored: " + ", and ".join(causes) + "."

def _print_evaluation_summary(summary: dict) -> None:
    # The counts of the Markdown summary (EvaluationReport.to_markdown), in its order: stale
    # predictions, the distractor hits, the branch-level and attribution failures and the fix
    # shapes had no line, so a FAIL they caused was not accounted for on stdout (issue #144).
    rows = [
        ("Total", summary["total_scenarios"]),
        ("PASS", summary["pass"]),
        ("FAIL", summary["fail"]),
        ("Tool errors", summary["tool_errors"]),
        ("Missing records", summary["missing_records"]),
        ("Stale predictions", summary["stale_predictions"]),
        ("Invalid records", summary["invalid_records"]),
        ("True positives", summary["true_positives"]),
        ("False positives", summary["false_positives"]),
        ("Unknown (as FP)", summary["unknown_predictions"]),
        ("False negatives", summary["false_negatives"]),
        ("Allowed FP", summary["allowed_false_positives"]),
        ("Hard FP", summary["hard_false_positives"]),
        ("Related origins", summary["related_origin_hits"]),
        ("Related not-correct", summary["related_but_not_correct_hits"]),
        ("Known distractor hits", summary["known_distractor_hits"]),
        ("Branch-level failures", f"{summary['branch_level_failures']} of {summary['branch_level_scenarios']} scenario(s)"),
        ("Attribution failures", f"{summary['attribution_failures']} of {summary['attribution_scenarios']} scenario(s)"),
        ("Fix shapes (per BFC)", _format_fix_shape_counts(summary["fix_shape_counts"])),
        ("Weighted credit", _display_credit(summary["weighted_credit"], summary["possible_credit"])),
        ("Precision", _display_ratio(summary["precision"])),
        ("Recall", _display_ratio(summary["recall"])),
    ]
    width = max(len(label) for label, _ in rows) + 2      # the colon and one space after the longest label
    print("Summary:")
    for label, value in rows:
        print(f"  {label + ':':<{width}}{value}")

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
        outputs = find_generated_outputs(root)
        if outputs and not args.dry_run:
            # outside the default root, nothing is removed without a yes (issue #171)
            if not args.yes and not is_default_clean_root(root) and not _confirm_clean(root.resolve(), outputs):
                return 1
            remove_generated_outputs(outputs)
    except CleanError as exc:
        print(f"[ERROR] CLEAN_FAILED: {exc}", file=sys.stderr)
        return 1
    root_display = root.resolve()
    if args.json:
        _print_json({
            "root": str(root_display),
            "dry_run": args.dry_run,
            "outputs": [str(output) for output in outputs],
            "summary": {"found": len(outputs), "removed": 0 if args.dry_run else len(outputs)},
        })
        return 0
    if not outputs:
        print(f"No generated repositories found under: {root_display}")
        return 0
    verb = "Would remove" if args.dry_run else "Removed"
    for output in outputs:
        print(f"{verb}: {output}")
    suffix = "found" if args.dry_run else "removed"
    print(f"Summary: {len(outputs)} generated output(s) {suffix}.")
    return 0

def _confirm_clean(root: Path, outputs: list[Path]) -> bool:
    """Ask on the terminal before ``clean`` removes the outputs under a root that is not the default.

    Everything goes to stderr, so that stdout keeps only what ``--json`` prints.
    """
    try:
        interactive = sys.stdin is not None and sys.stdin.isatty()
    except ValueError:                          # a closed stdin
        interactive = False
    if not interactive:
        print(f"[ERROR] CLEAN_FAILED: {len(outputs)} generated output(s) found under {root}, which is not the default "
              f"root {DEFAULT_CLEAN_ROOT}; clean asks before removing them there, and stdin is not a terminal. "
              "Check them with --dry-run, then pass --yes. Nothing was removed.", file=sys.stderr)
        return False
    for output in outputs:
        print(f"Would remove: {output}", file=sys.stderr)
    print(f"Remove these {len(outputs)} generated output(s) under {root}? [y/N] ", end="", file=sys.stderr, flush=True)
    if sys.stdin.readline().strip().lower() in ("y", "yes"):
        return True
    print("Nothing was removed.", file=sys.stderr)
    return False

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

def _display_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _display_credit(weighted_credit: float | None, possible_credit: float | None) -> str:
    if weighted_credit is None or possible_credit is None:
        return "-"
    return f"{weighted_credit:.3f}/{possible_credit:.3f}"


def _add_verification_options(parser: argparse.ArgumentParser, no_verify_help: str, *,
                              strict_help: str = "Treat verification warnings as failures") -> None:
    """``--no-verify``, ``--strict`` and ``--json`` of the generate commands (issue #169).

    ``--strict`` with ``--no-verify`` would pass without a check, so argparse refuses the pair.
    """
    exclusive = parser.add_mutually_exclusive_group()
    exclusive.add_argument("--no-verify", action="store_true", help=no_verify_help)
    exclusive.add_argument("--strict", action="store_true", help=strict_help)
    parser.add_argument("--json", action="store_true", help="Print JSON output")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="szzbench")
    sub = parser.add_subparsers(dest="command", required=True)
    p_validate = sub.add_parser("validate", help="Validate scenario.yml")
    p_validate.add_argument("scenario")
    p_validate.add_argument("--simulate", action="store_true", help="Also simulate operations in memory")
    p_validate.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    p_validate.add_argument("--lint", action="store_true", help="Run opt-in lints (W4xx warnings; implies --simulate)")
    p_validate.add_argument("--json", action="store_true", help="Print JSON output")
    p_validate.set_defaults(func=cmd_validate)
    p_generate = sub.add_parser("generate", help="Generate a synthetic Git repository from scenario.yml")
    p_generate.add_argument("scenario")
    p_generate.add_argument("--out", required=True, help="Output directory containing repo/ and metadata/")
    p_generate.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    _add_verification_options(p_generate, "Skip post-generation verification")
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
    p_validate_graph.add_argument("--lint", action="store_true", help="Run opt-in lints (GW4xx warnings)")
    p_validate_graph.add_argument("--json", action="store_true", help="Print JSON output")
    p_validate_graph.set_defaults(func=cmd_validate_graph)

    p_validate_index = sub.add_parser("validate-index", help="Check scenarios/index.yml and advanced-scenarios/index.yml against the scenario directories")
    p_validate_index.add_argument("--scenarios-root", default=str(DEFAULT_SCENARIOS_ROOT), help="Root directory for classic scenarios")
    p_validate_index.add_argument("--advanced-scenarios-root", default=str(DEFAULT_ADVANCED_SCENARIOS_ROOT), help="Root directory for graph scenarios")
    p_validate_index.add_argument("--json", action="store_true", help="Print JSON output")
    p_validate_index.set_defaults(func=cmd_validate_index)

    p_generate_graph = sub.add_parser("generate-graph", help="Generate a synthetic Git repository from scenario.graph.yml")
    p_generate_graph.add_argument("scenario")
    p_generate_graph.add_argument("--out", required=True, help="Output directory containing repo/ and metadata/")
    p_generate_graph.add_argument("--force", action="store_true", help="Overwrite output directory if it exists")
    _add_verification_options(p_generate_graph, "Skip post-generation graph verification")
    p_generate_graph.set_defaults(func=cmd_generate_graph)

    p_generate_all = sub.add_parser("generate-all-repos", help="Generate repositories for every classic and graph scenario")
    p_generate_all.add_argument("--overwrite", action="store_true", help="Overwrite existing generated repositories")
    _add_verification_options(p_generate_all, "Skip post-generation verification",
                              strict_help="Exit 1 when the verification of any output has a warning, a skipped "
                                          "output's recorded one included")
    p_generate_all.add_argument("--out-root", default=str(DEFAULT_GENERATED_INPUT_REPOS_ROOT), help="Root directory for generated repositories")
    p_generate_all.add_argument("--scenarios-root", default=str(DEFAULT_SCENARIOS_ROOT), help="Root directory for classic scenarios")
    p_generate_all.add_argument("--advanced-scenarios-root", default=str(DEFAULT_ADVANCED_SCENARIOS_ROOT), help="Root directory for graph scenarios")
    p_generate_all.set_defaults(func=cmd_generate_all_repos)

    p_verify_graph = sub.add_parser("verify-graph", help="Verify a generated repository against scenario.graph.yml")
    p_verify_graph.add_argument("repo")
    p_verify_graph.add_argument("--scenario", required=True)
    p_verify_graph.add_argument("--commit-map", help="Path to commit-map.json")
    p_verify_graph.add_argument("--graph-map", help="Path to graph-map.json")
    p_verify_graph.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    p_verify_graph.add_argument("--json", action="store_true", help="Print JSON output")
    p_verify_graph.set_defaults(func=cmd_verify_graph)

    p_baselines = sub.add_parser("baselines", help="Score cheap baselines to show what SZZBench does not test")
    p_baselines.add_argument("--generated-root", default=str(DEFAULT_GENERATED_INPUT_REPOS_ROOT), help="Root directory for generated repositories")
    p_baselines.add_argument("--scenarios-root", default=str(DEFAULT_SCENARIOS_ROOT), help="Root directory for classic scenarios")
    p_baselines.add_argument("--advanced-scenarios-root", default=str(DEFAULT_ADVANCED_SCENARIOS_ROOT), help="Root directory for graph scenarios")
    p_baselines.add_argument("--variant", default="default", help="Generated repository variant name under each scenario")
    p_baselines.add_argument("--family", action="append", choices=list(BASELINE_FAMILIES), help="Only run these families (repeatable); default: all")
    p_baselines.add_argument("--out", help="Write baselines.json and baselines.md to this directory")
    p_baselines.add_argument("--json", action="store_true", help="Print JSON output")
    p_baselines.set_defaults(func=cmd_baselines)

    p_coverage = sub.add_parser("coverage", help="Report what each scenario contributes: difficulty dimensions and redundancy")
    p_coverage.add_argument("--generated-root", default=str(DEFAULT_GENERATED_INPUT_REPOS_ROOT), help="Root directory for generated repositories")
    p_coverage.add_argument("--scenarios-root", default=str(DEFAULT_SCENARIOS_ROOT), help="Root directory for classic scenarios")
    p_coverage.add_argument("--advanced-scenarios-root", default=str(DEFAULT_ADVANCED_SCENARIOS_ROOT), help="Root directory for graph scenarios")
    p_coverage.add_argument("--variant", default="default", help="Generated repository variant name under each scenario")
    p_coverage.add_argument("--out", help="Write coverage.json and coverage.md to this directory")
    p_coverage.add_argument("--json", action="store_true", help="Print JSON output")
    p_coverage.set_defaults(func=cmd_coverage)

    p_readme = sub.add_parser("readme", help="Check or regenerate the generated header of every scenario README")
    p_readme.add_argument("scenarios", nargs="*", help="Scenario files or directories (default: every scenario of both suites)")
    p_readme.add_argument("--scenarios-root", default=str(DEFAULT_SCENARIOS_ROOT), help="Root directory for classic scenarios")
    p_readme.add_argument("--advanced-scenarios-root", default=str(DEFAULT_ADVANCED_SCENARIOS_ROOT), help="Root directory for graph scenarios")
    p_readme.add_argument("--write", action="store_true", help="Rewrite missing or stale headers and drop the hand-written Factors/Source copies")
    p_readme.add_argument("--json", action="store_true", help="Print JSON output")
    p_readme.set_defaults(func=cmd_readme)

    p_evaluate = sub.add_parser("evaluate", help="Evaluate SZZ tool predictions against SZZBench oracles")
    p_evaluate.add_argument("--predictions", help="Path to predictions JSON or JSONL")
    p_evaluate.add_argument("--generated-root", default=str(DEFAULT_GENERATED_INPUT_REPOS_ROOT), help="Root directory for generated repositories")
    p_evaluate.add_argument("--scenarios-root", default=str(DEFAULT_SCENARIOS_ROOT), help="Root directory for classic scenarios")
    p_evaluate.add_argument("--advanced-scenarios-root", default=str(DEFAULT_ADVANCED_SCENARIOS_ROOT), help="Root directory for graph scenarios")
    p_evaluate.add_argument("--variant", default="default", help="Generated repository variant name under each scenario")
    p_evaluate.add_argument("--include-generated", action="store_true", help="Evaluate every generated repository under --generated-root, using empty predictions for missing records")
    p_evaluate.add_argument("--evaluation-variant", help="Graph scenario evaluation variant name to use, overriding expected_szz.default_variant")
    p_evaluate.add_argument(
        "--reference-format",
        choices=["auto", "hash", "logical"],
        default="auto",
        help="How predicted commits may be written: 'hash' accepts only commit hashes, which is all a tool that reads the "
             "repository can produce; 'logical' accepts only scenario ids such as c1, for adapters and fixtures; 'auto' "
             "(default) accepts both. Rejected references are reported as unknown predictions.",
    )
    p_evaluate.add_argument("--out", help="Output directory for evaluation-results.json and evaluation-results.md")
    p_evaluate.add_argument("--json", action="store_true", help="Print JSON output")
    p_evaluate.add_argument("--fail-on-non-pass", action="store_true", help="Return a non-zero exit code when any scenario is non-PASS")
    p_evaluate.set_defaults(func=cmd_evaluate)

    p_new_graph = sub.add_parser("new-graph-scenario", help="Create a new graph scenario skeleton")
    p_new_graph.add_argument("--title", required=True, help="Graph scenario title")
    p_new_graph.add_argument("--category", required=True, help="Graph scenario category")
    p_new_graph.add_argument("--root", default=str(DEFAULT_GRAPH_SCENARIOS_ROOT), help="Graph scenario root directory")
    p_new_graph.add_argument("--slug", help="Override the generated slug")
    p_new_graph.add_argument("--factor", action="append", default=[], help="Graph scenario factor; can be repeated")
    p_new_graph.add_argument("--difficulty", default="medium", choices=SCENARIO_DIFFICULTIES,
                             help="Graph scenario difficulty (default: medium; check it against the measured floor with 'szzbench coverage')")
    p_new_graph.add_argument("--status", default="draft", help="Graph scenario status")
    p_new_graph.set_defaults(func=cmd_new_graph_scenario)

    p_clean = sub.add_parser("clean", help="Remove generated repositories")
    p_clean.add_argument("--root", default=str(DEFAULT_CLEAN_ROOT), help="Root directory to scan for generated outputs")
    p_clean.add_argument("--dry-run", action="store_true", help="Show generated outputs without removing them")
    p_clean.add_argument("--yes", action="store_true",
                         help="Remove without asking when --root is not the default generated-input-repos")
    p_clean.add_argument("--json", action="store_true", help="Print JSON output")
    p_clean.set_defaults(func=cmd_clean)
    p_new = sub.add_parser("new-scenario", help="Create a new scenario skeleton")
    p_new.add_argument("--title", required=True, help="Scenario title")
    p_new.add_argument("--category", required=True, help="Scenario category")
    p_new.add_argument("--root", default=str(DEFAULT_SCENARIOS_ROOT), help="Scenario root directory")
    p_new.add_argument("--slug", help="Override the generated slug")
    p_new.add_argument("--factor", action="append", default=[], help="Scenario factor; can be repeated")
    p_new.add_argument("--difficulty", default="medium", choices=SCENARIO_DIFFICULTIES,
                       help="Scenario difficulty (default: medium; check it against the measured floor with 'szzbench coverage')")
    p_new.add_argument("--status", default="draft", help="Scenario status")
    p_new.set_defaults(func=cmd_new_scenario)
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
