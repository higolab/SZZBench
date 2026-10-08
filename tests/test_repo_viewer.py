"""The Generated repository viewer's API runs git only on what it was meant to (issue #132).

``tools/generated-repo-viewer/server/index.js`` checked ``target`` against the
project root but handed ``commit`` and ``file`` to ``git show``, ``git ls-tree``
and ``git blame`` as they came, where git reads its own options: a ``commit``
of ``--output=<path>`` made git write to that path.  The server also answered
every origin (``cors()``), so any page open in the same browser could send
such a request, and its error responses carried git's messages with absolute
paths.  These tests start the server on a scratch copy of the layout and send
it the requests a browser would.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from support import git
from szzbench.generator import generate_repository

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "tools/generated-repo-viewer"
TARGET = "generated-input-repos/SZZ-0006/default"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="module")
def viewer(tmp_path_factory):
    if not (VIEWER / "node_modules/express").is_dir():
        pytest.skip("needs the viewer's dependencies (npm ci in tools/generated-repo-viewer)")
    root = tmp_path_factory.mktemp("layout")
    out = root / TARGET
    _, verify = generate_repository(ROOT / "scenarios/SZZ-0006/scenario.yml", out, force=True)
    assert verify is not None and not verify.has_errors()
    port = _free_port()
    process = subprocess.Popen(["node", str(VIEWER / "server/index.js")], cwd=VIEWER,
                               env={**os.environ, "SZZBENCH_REPO_VIEWER_PORT": str(port),
                                    "SZZBENCH_REPO_ROOT": str(root)},
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    else:
        process.kill()
        pytest.fail("the viewer server did not start")
    commit_map = json.loads((out / "metadata/commit-map.json").read_text(encoding="utf-8"))
    yield base, root, commit_map
    process.kill()
    process.wait()


def _get(base: str, endpoint: str, headers: dict | None = None, **query) -> tuple[int, dict, dict]:
    url = f"{base}/api/{endpoint}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), json.loads(error.read())


def _head_and_file(commit_map: dict) -> tuple[str, str, str]:
    bfc = commit_map["c2"]["hash"]
    return bfc, commit_map["c1"]["hash"], "src/main/java/example/Scenario0006.java"


# --- what the viewer is for still works -----------------------------------------

def test_the_four_routes_answer_a_valid_request(viewer):
    base, root, commit_map = viewer
    bfc, bic, file = _head_and_file(commit_map)
    assert _get(base, "tree", target=TARGET, commit=bfc)[2] == {"files": [file]}
    status, _, body = _get(base, "file", target=TARGET, commit=bfc, file=file)
    assert status == 200 and body["content"] == git(root / TARGET / "repo", "show", f"{bfc}:{file}") + "\n"
    status, _, body = _get(base, "diff", target=TARGET, commit=bfc, file=file)
    assert status == 200 and body["diff"].startswith(f"diff --git a/{file} b/{file}")
    status, _, body = _get(base, "diff", target=TARGET, commit=bfc)
    assert status == 200 and f"b/{file}" in body["diff"]
    status, _, body = _get(base, "blame", target=TARGET, commit=bic, file=file)
    assert status == 200 and bic in {line["hash"] for line in body["lines"]}


def test_an_abbreviated_hash_is_still_a_commit(viewer):
    base, _, commit_map = viewer
    bfc, _, file = _head_and_file(commit_map)
    assert _get(base, "tree", target=TARGET, commit=bfc[:7])[2] == {"files": [file]}


# --- request values never reach git as options ---------------------------------

@pytest.mark.parametrize("endpoint", ["diff", "file", "tree", "blame"])
def test_a_commit_that_reads_as_an_option_is_refused_and_git_writes_nothing(viewer, tmp_path, endpoint):
    base, _, commit_map = viewer
    _, _, file = _head_and_file(commit_map)
    written = tmp_path / "written-by-git.txt"
    status, _, body = _get(base, endpoint, target=TARGET, commit=f"--output={written}", file=file)
    assert (status, body) == (400, {"error": "Invalid commit: expected a commit hash."})
    assert not written.exists()


@pytest.mark.parametrize("commit", ["HEAD", "main", "c2", "-p", "e68f db9", "g" * 40, "a" * 65])
def test_only_a_hash_names_a_commit(viewer, commit):
    base, _, _ = viewer
    assert _get(base, "tree", target=TARGET, commit=commit)[0] == 400


@pytest.mark.parametrize("endpoint", ["file", "diff", "blame"])
@pytest.mark.parametrize("file", ["/etc/passwd", "../../../../etc/passwd", "src/../../x", "src//x", "src\\x", "C:/x"])
def test_a_file_outside_the_tree_is_refused(viewer, endpoint, file):
    base, root, commit_map = viewer
    bfc, _, _ = _head_and_file(commit_map)
    status, _, body = _get(base, endpoint, target=TARGET, commit=bfc, file=file)
    assert (status, body) == (400, {"error": "Invalid file: expected a path inside the repository."})


def test_a_file_that_starts_with_a_dash_is_a_path_not_an_option(viewer, tmp_path):
    base, _, commit_map = viewer
    bfc, _, _ = _head_and_file(commit_map)
    written = tmp_path / "written-by-git.txt"
    # a path no commit has: the diff is empty, and blame and show find nothing to read
    assert _get(base, "diff", target=TARGET, commit=bfc, file=f"--output={written}")[:3:2] == (200, {"diff": ""})
    assert _get(base, "blame", target=TARGET, commit=bfc, file=f"--output={written}")[0] == 400
    assert _get(base, "file", target=TARGET, commit=bfc, file=f"--output={written}")[0] == 400
    assert not written.exists()


# --- other sites and the server's own paths -------------------------------------

def test_no_cors_header_is_sent(viewer):
    base, _, _ = viewer
    _, headers, _ = _get(base, "health", headers={"Origin": "https://example.org"})
    assert not any(name.lower().startswith("access-control-") for name in headers)


@pytest.mark.parametrize("site, status", [("cross-site", 403), ("same-site", 403), ("same-origin", 200), ("none", 200)])
def test_a_request_a_browser_marks_as_another_sites_is_refused(viewer, site, status):
    base, _, commit_map = viewer
    bfc, _, _ = _head_and_file(commit_map)
    assert _get(base, "tree", headers={"Sec-Fetch-Site": site}, target=TARGET, commit=bfc)[0] == status


def test_a_git_error_does_not_reveal_the_servers_paths(viewer):
    base, root, _ = viewer
    status, _, body = _get(base, "tree", target=TARGET, commit="0" * 40)
    assert status == 400
    assert str(root) not in body["error"] and os.sep + "Users" not in body["error"]
    assert body["error"] == "The request could not be served; the server log has the details."


def test_a_symlink_out_of_the_project_is_not_followed(viewer, tmp_path):
    base, root, _ = viewer
    outside = tmp_path / "outside"
    shutil.copytree(root / TARGET, outside)
    link = root / "generated-input-repos/SZZ-9999"
    link.symlink_to(outside, target_is_directory=True)
    try:
        status, _, body = _get(base, "repository", target="generated-input-repos/SZZ-9999")
        assert (status, body) == (400, {"error": "Path escapes the SZZBench project root."})
    finally:
        link.unlink()
