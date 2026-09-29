"""The tests run against this checkout's ``src`` (issue #107).

Twenty-three test modules put ``src`` on ``sys.path`` themselves, the others
relied on an installed package, and the tests that run ``python -m
szzbench.cli`` in a subprocess failed without ``pip install -e .`` -- or ran
the code of whatever checkout the installed package pointed at.  Putting
``src`` first on both ``sys.path`` and ``PYTHONPATH`` makes every test, and
every subprocess it starts, exercise the code next to it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parents[1] / "src")
sys.path.insert(0, SRC)
os.environ["PYTHONPATH"] = os.pathsep.join(path for path in (SRC, os.environ.get("PYTHONPATH")) if path)
