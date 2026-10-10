"""The licence files name the SZZBench authors, and the package carries its licence metadata (issue #204).

`LICENSE-MIT` named "Anonymous Authors" as the copyright holder and
`LICENSES.md` asked for the same attribution "during anonymous review", and
`pyproject.toml` declared no readme, licence, licence files, authors or URLs,
so an installed or built package carried none of them.  The first test keeps
the placeholders out; the second checks that `pyproject.toml` declares the
licences that `LICENSES.md` applies, as an SPDX expression, and names licence
files that exist, so that a wheel ships the texts.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPOSITORY_URL = "https://github.com/higolab/SZZBench"


def test_the_licence_files_name_the_szzbench_authors_not_an_anonymous_placeholder():
    assert "Copyright (c) 2026 The SZZBench authors" in (REPO / "LICENSE-MIT").read_text(encoding="utf-8")
    assert f"> The SZZBench authors, *SZZBench*, {REPOSITORY_URL}" in (REPO / "LICENSES.md").read_text(encoding="utf-8")
    for name in ("LICENSE-MIT", "LICENSES.md", "README.md", "pyproject.toml"):
        text = (REPO / name).read_text(encoding="utf-8")
        assert re.findall(r"anonymous[ -](?:authors|review)", text, re.IGNORECASE) == [], name


def test_pyproject_declares_the_licences_of_licenses_md_and_the_files_that_hold_them():
    tomllib = pytest.importorskip("tomllib", reason="tomllib is in the standard library from Python 3.11")
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    applied = re.findall(r"SPDX identifier:\s*`([^`]+)`", (REPO / "LICENSES.md").read_text(encoding="utf-8"))
    assert sorted(project["license"].split(" AND ")) == sorted(applied) == ["CC-BY-4.0", "MIT"]
    assert sorted(project["license-files"]) == ["LICENSE-CC-BY-4.0", "LICENSE-MIT", "LICENSES.md"]
    assert [name for name in [*project["license-files"], project["readme"]] if not (REPO / name).is_file()] == []
    assert project["authors"] and all(author.get("name") and author.get("email") for author in project["authors"])
    assert project["urls"]["Homepage"] == REPOSITORY_URL
