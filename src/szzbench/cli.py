from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .generator import GenerationError, generate_repository
from .validator import validate_scenario_file
from .verifier import verify_generated_repo

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
    return parser

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
