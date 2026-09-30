#!/usr/bin/env python3
"""Token-level B-SZZ over SZZBench's generated repositories.

The MV-SZZ replication package runs B-SZZ on token-level histories: cregit's
tokenizer rewrites every Java file of every commit into one token per line (or
N tokens per line), and B-SZZ then blames tokens instead of lines. This script
does the same in three steps:

1. tokenize: run tools/adapters/token-bszz/tokenize-repos.sh in the image built
   from that directory, which rewrites each generated repository into --token-root;
2. B-SZZ: give each token-level repository the metadata SZZBench wrote for the
   original (its commit map re-keyed to the rewritten hashes) and run
   tools/adapters/pyszz_variants_to_predictions.py --tools b-szz on them;
3. map back: name each predicted commit by the original repository's hash,
   through the `Former-commit-id` footer that BFG adds to every commit it rewrites.

Only .java files are tokenized; every other file keeps its lines.
examples/token-bszz-run/README.md says what to install and records a run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ADAPTERS = Path(__file__).resolve().parent
FORMER_COMMIT = re.compile(r"^Former-commit-id: ([0-9a-f]{40})$", re.M)
TOOL = "token-b-szz"
#: fields of PySZZ's predictions left out: positions in the token-level files, the path of its raw
#: output, and the scenario id the record already names
DROPPED_FIELDS = {"line", "line_content", "input_line", "raw_file", "scenario_id"}
#: the record, in --token-root, of how its repositories were tokenized, which --skip-tokenize checks
TOKENIZATION = "tokenization.json"


class CannotReuse(Exception):
    """A token root whose repositories --skip-tokenize cannot reuse for the settings asked for."""


class IncompleteOutput(ValueError):
    """A generated output whose commit map is missing, unreadable, or not a JSON object."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--generated-root", default="generated-input-repos", type=Path,
                        help="Root containing generated SZZBench repositories.")
    parser.add_argument("--variant", default="default", help="Generated repository variant name under each scenario.")
    parser.add_argument("--token-root", required=True, type=Path,
                        help="Where the token-level repositories and their metadata go.")
    parser.add_argument("--cregit-root", required=True, type=Path,
                        help="The replication package's modified cregit: the cregit directory of tools/cregit.zip.")
    parser.add_argument("--pyszz-root", required=True, type=Path,
                        help="PySZZ, as for pyszz_variants_to_predictions.py --tool-root.")
    parser.add_argument("--pyszz-python", default=sys.executable,
                        help="The Python with the libraries PySZZ imports (default: this one).")
    parser.add_argument("--image", default="szzbench-token-bszz", help="The image built from tools/adapters/token-bszz.")
    parser.add_argument("--docker", default="docker", help="The docker executable.")
    parser.add_argument("--window-size", type=int, default=1, help="Tokens per line (the replication package's N).")
    parser.add_argument("--skip-tokenize", action="store_true",
                        help=f"Reuse the token-level repositories a previous run left in --token-root. They must "
                             f"have been tokenized with the same --variant and --window-size, as its {TOKENIZATION} "
                             "records.")
    parser.add_argument("--out", required=True, type=Path, help="Output predictions JSONL path.")
    args = parser.parse_args(argv)

    generated_root = args.generated_root.resolve()
    token_root = args.token_root.resolve()
    token_root.mkdir(parents=True, exist_ok=True)
    tokenization_path = token_root / TOKENIZATION
    requested = {"variant": args.variant, "window_size": args.window_size}
    if args.skip_tokenize:
        try:
            tokenization = reused_tokenization(tokenization_path, requested)
        except CannotReuse as exc:
            print(f"[ERROR] --skip-tokenize: {exc}. Tokenize them again without --skip-tokenize.", file=sys.stderr)
            return 2
    else:
        # a tokenization that stops part way leaves no record, so it cannot be reused as a finished one
        tokenization_path.unlink(missing_ok=True)
        command = [args.docker, "run", "--rm", "--platform", "linux/amd64",
                   "-e", f"BFG_WINDOW_SIZE={args.window_size}", "-e", f"VARIANT={args.variant}",
                   "-v", f"{generated_root}:/in:ro", "-v", f"{token_root}:/out",
                   "-v", f"{args.cregit_root.resolve()}:/opt/cregit:ro", args.image, "tokenize-repos.sh"]
        subprocess.run(command, check=True)
        tokenization = {**requested, "image": _image_id(args.docker, args.image)}
        tokenization_path.write_text(json.dumps(tokenization, indent=2) + "\n", encoding="utf-8")

    home = tempfile.mkdtemp(prefix="token-bszz-home-")
    atexit.register(shutil.rmtree, home, True)
    environment = isolated_environment(dict(os.environ), home)
    mappings, failures = prepare_token_outputs(generated_root, token_root, args.variant, environment)

    work = args.out.resolve().parent / "pyszz"
    b_szz_predictions = work / "b-szz" / "b-szz-predictions.jsonl"
    # the adapter clears this directory only once B-SZZ starts, so a run that stops earlier would
    # leave the previous run's records to be read as this run's
    if b_szz_predictions.parent.exists():
        shutil.rmtree(b_szz_predictions.parent)
    completed = subprocess.run([args.pyszz_python, str(ADAPTERS / "pyszz_variants_to_predictions.py"),
                                "--tool-root", str(args.pyszz_root.resolve()), "--generated-root", str(token_root),
                                "--output-root", str(work), "--variant", args.variant, "--tools", "b-szz",
                                "--log-file", str(work / "b-szz.log")])
    # 1 says that some records carry tool errors, which they name; a crash exits 1 too, but writes no records
    if completed.returncode not in (0, 1) or not b_szz_predictions.exists():
        print(f"[ERROR] B-SZZ did not finish: pyszz_variants_to_predictions.py exited with status "
              f"{completed.returncode}{'' if b_szz_predictions.exists() else ' and wrote no records'}", file=sys.stderr)
        return 2

    records = map_back(b_szz_predictions, mappings, failures)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    summary = {
        "tool": TOOL,
        # how the repositories B-SZZ ran on were tokenized, which a reuse takes from the record
        "window_size": tokenization["window_size"],
        "image": tokenization.get("image"),
        "scenario_count": len(records),
        "error_count": sum(1 for record in records if record.get("status") == "error"),
        "pyszz_environment": _pyszz_environment(work / "b-szz" / "b-szz-run-results.json"),
    }
    args.out.with_name("token-bszz-run.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for record in records:
        for error in record.get("errors", []):
            print(f"[ERROR] {record['scenario_id']}: {error}", file=sys.stderr)
    return 1 if summary["error_count"] else 0


def reused_tokenization(path: Path, requested: dict[str, Any]) -> dict[str, Any]:
    """The recorded tokenization of a token root, when it matches the settings asked for.

    Reusing the repositories under other settings would label one tokenization's
    answers with another's settings, so CannotReuse says why the record is
    missing or does not match.
    """
    try:
        recorded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        recorded = None
    if not isinstance(recorded, dict):
        raise CannotReuse(f"{path} does not record how the repositories under {path.parent} were tokenized")
    differing = [key for key, value in requested.items() if recorded.get(key) != value]
    if differing:
        def as_options(settings: dict[str, Any]) -> str:
            return " ".join(f"--{key.replace('_', '-')} {settings.get(key)}" for key in differing)
        raise CannotReuse(f"the repositories under {path.parent} were tokenized with {as_options(recorded)}, "
                          f"not {as_options(requested)}")
    return recorded


def prepare_token_outputs(generated_root: Path, token_root: Path, variant: str,
                          environment: dict[str, str]) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Prepare every generated output's token-level copy.

    Returns each scenario's map from token-level to original commits, and the
    error of each scenario that could not be prepared. Every generated
    repository gets one or the other: an incomplete output is a tool error,
    not a scenario to leave out (issue #95).
    """
    mappings: dict[str, dict[str, str]] = {}
    failures: dict[str, str] = {}
    for repo in sorted(generated_root.glob(f"*/{variant}/repo")):
        original = repo.parent
        scenario_id = original.parent.name
        try:
            mappings[scenario_id] = prepare_token_output(original, token_root / scenario_id / variant, environment)
        except IncompleteOutput as exc:
            failures[scenario_id] = str(exc)
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            failures[scenario_id] = f"{type(exc).__name__}: {exc}"
    return mappings, failures


def prepare_token_output(original: Path, token: Path, environment: dict[str, str]) -> dict[str, str]:
    """Give a token-level repository the original's metadata, re-keyed to its hashes.

    Returns the map from each token-level commit to the original commit it was
    rewritten from.  Raises IncompleteOutput when the original's commit map
    cannot be used, and ValueError when tokenization failed or a commit of the
    original's commit map has no rewritten counterpart.
    """
    commit_map = read_commit_map(original / "metadata" / "commit-map.json")
    status = (token / "tokenize.status").read_text(encoding="utf-8").strip() if (token / "tokenize.status").exists() else None
    if status != "0" or not (token / "repo").is_dir():
        raise ValueError(f"tokenization failed (status {status}; see {token / 'tokenize.log'})")
    to_original = former_commit_map(token / "repo", environment)
    to_token = {original_hash: token_hash for token_hash, original_hash in to_original.items()}
    # BFG rewrites the history the refs reach; a commit no ref reaches (a deleted branch's) has no
    # token-level counterpart, and no tool reading the repository can name it either
    reachable = set(subprocess.run(["git", "rev-list", "--all"], cwd=original / "repo", env=environment,
                                   capture_output=True, text=True, check=True).stdout.split())
    rekeyed = {}
    for logical_id, entry in commit_map.items():
        if not (isinstance(entry, dict) and isinstance(entry.get("hash"), str)):
            rekeyed[logical_id] = entry
            continue
        if entry["hash"] not in to_token:
            if entry["hash"] not in reachable:
                continue
            raise ValueError(f"{logical_id} ({entry['hash'][:10]}) has no token-level commit")
        rekeyed[logical_id] = {**entry, "hash": to_token[entry["hash"]]}
    metadata = token / "metadata"
    if metadata.exists():
        shutil.rmtree(metadata)
    metadata.mkdir(parents=True)
    for name in ("scenario.yml", "scenario.graph.yml", "manifest.json"):
        if (original / "metadata" / name).exists():
            shutil.copyfile(original / "metadata" / name, metadata / name)
    (metadata / "commit-map.json").write_text(json.dumps(rekeyed, indent=2) + "\n", encoding="utf-8")
    (metadata / "token-to-original.json").write_text(json.dumps(to_original, indent=2) + "\n", encoding="utf-8")
    return to_original


def read_commit_map(path: Path) -> dict[str, Any]:
    """A generated output's commit map. IncompleteOutput says what is wrong with one that cannot be used."""
    try:
        commit_map = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        problem = "is missing" if not path.exists() else f"cannot be read ({type(exc).__name__}: {exc})"
        raise IncompleteOutput(f"{path} {problem}: the generated output is incomplete") from exc
    if not isinstance(commit_map, dict):
        kind = {list: "an array", str: "a string", bool: "a boolean", int: "a number", float: "a number"}.get(
            type(commit_map), "null")
        raise IncompleteOutput(f"{path} holds {kind}, not a JSON object: the generated output is incomplete")
    return commit_map


def former_commit_map(repo: Path, environment: dict[str, str]) -> dict[str, str]:
    """Each commit of a BFG-rewritten repository mapped to the commit it was rewritten from.

    BFG adds `Former-commit-id: <hash>` to every commit it changes; a commit it
    left alone keeps its hash, and maps to itself.  This is the mapping cregit's
    remapCommits builds from the same footer.
    """
    log = subprocess.run(["git", "log", "--all", "--format=%H%x00%B%x01"], cwd=repo, env=environment,
                         capture_output=True, text=True, check=True).stdout
    mapping = {}
    for entry in log.split("\x01"):
        entry = entry.strip("\n")
        if not entry:
            continue
        commit, _, message = entry.partition("\x00")
        former = FORMER_COMMIT.findall(message)
        mapping[commit] = former[-1] if former else commit
    return mapping


def map_back(predictions_path: Path, mappings: dict[str, dict[str, str]], failures: dict[str, str]) -> list[dict[str, Any]]:
    """B-SZZ's records on the token-level repositories, named by the original repositories' hashes.

    A scenario whose preparation failed gets its failure, which names the cause, whatever B-SZZ
    wrote for its incomplete copy.
    """
    records = []
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        scenario_id = record["scenario_id"]
        if scenario_id in failures:
            continue
        mapping = mappings.get(scenario_id, {})
        errors = list(record.get("errors", []))
        predictions = []
        for prediction in record.get("predictions", []):
            # line numbers count tokens of the token-level file, not lines of the original
            prediction = {key: value for key, value in prediction.items() if key not in DROPPED_FIELDS}
            for key in ("fix_commit", "inducing_commit"):
                if key in prediction:
                    if prediction[key] not in mapping:
                        errors.append(f"{key} {prediction[key][:10]} is not a commit of the token-level repository")
                        continue
                    prediction[key] = mapping[prediction[key]]
            prediction["tool"] = TOOL
            predictions.append(prediction)
        mapped: dict[str, Any] = {"scenario_id": scenario_id, "predictions": predictions}
        if record.get("repository_id"):
            mapped["repository_id"] = record["repository_id"]
        if errors:
            mapped["status"] = "error"
            mapped["errors"] = errors
        records.append(mapped)
    for scenario_id, failure in failures.items():
        records.append({"scenario_id": scenario_id, "status": "error", "errors": [failure], "predictions": []})
    return sorted(records, key=lambda record: record["scenario_id"])


def isolated_environment(environ: dict[str, str], home: str) -> dict[str, str]:
    """SZZBench's Git isolation (issue #96) for the git this script runs."""
    isolated = {key: value for key, value in environ.items()
                if not key.startswith("GIT_") or key == "GIT_EXEC_PATH"}
    isolated.update({"HOME": home, "XDG_CONFIG_HOME": home, "GIT_CONFIG_NOSYSTEM": "1", "GIT_ATTR_NOSYSTEM": "1"})
    return isolated


def _image_id(docker: str, image: str) -> str | None:
    try:
        completed = subprocess.run([docker, "image", "inspect", "--format", "{{.Id}}", image],
                                   capture_output=True, text=True)
    except OSError:
        return None
    return completed.stdout.strip() or None


def _pyszz_environment(results: Path) -> Any:
    try:
        return json.loads(results.read_text(encoding="utf-8")).get("environment")
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
