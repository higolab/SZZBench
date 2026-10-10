"""An encoding with a NUL character is E042, not a traceback (issue #276).

``operations.resolve_encoding`` asks ``codecs.lookup``, which refuses a NUL in
the name with ``ValueError``; the classic validator caught ``OperationError``
only, so ``validate`` (``--json`` included) and ``generate`` ended in a
traceback.  The graph validator reports the same name as GE061 since #240.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

from support import scenario_file

ROOT = Path(__file__).resolve().parents[1]


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


def test_a_nul_in_an_encoding_is_e042_in_validate_and_stops_generate(tmp_path):
    data = yaml.safe_load(scenario_file("SZZ-0005").read_text(encoding="utf-8"))
    data["commits"][0]["operations"][0]["encoding"] = "utf\x00"
    path = tmp_path / "SZZ-0005" / "scenario.yml"
    path.parent.mkdir()
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    completed = _szzbench(tmp_path, "validate", "--json", "SZZ-0005/scenario.yml")
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    errors = [(f["code"], f["location"], f["message"]) for f in json.loads(completed.stdout)["findings"]
              if f["severity"] == "ERROR"]
    assert errors == [("E042", "commits[0].operations[0].encoding",
                       "Operation 'write_file' encoding must be 'utf-8' or 'utf-8-sig', got 'utf\\x00'.")]
    completed = _szzbench(tmp_path, "generate", "SZZ-0005/scenario.yml", "--out", "out")
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    assert "validation failed" in completed.stderr and not (tmp_path / "out").exists()
