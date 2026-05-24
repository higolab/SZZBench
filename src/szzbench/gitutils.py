from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess


class GitError(RuntimeError):
    pass


def _git_env(extra_env: dict | None = None) -> dict:
    """Return an environment for Git subprocesses.

    On Windows, Python's default text encoding may be cp932. Git output can
    contain UTF-8 commit messages or paths, so run_git() decodes subprocess
    output explicitly as UTF-8. These environment values also encourage Git to
    produce UTF-8 output where supported.
    """
    git_env = os.environ.copy()
    git_env.setdefault("LANG", "C.UTF-8")
    git_env.setdefault("LC_ALL", "C.UTF-8")
    if extra_env:
        git_env.update(extra_env)
    return git_env


def run_git(repo_dir: Path, args: list[str], *, env: dict | None = None, capture: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            env=_git_env(env),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout
        raise GitError(f"git {' '.join(args)} failed: {detail}") from exc


def init_repo(repo_dir: Path, branch: str) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)
    run_git(repo_dir, ["init"])
    run_git(repo_dir, ["branch", "-M", branch])
    run_git(repo_dir, ["config", "user.name", "SZZ Benchmark"])
    run_git(repo_dir, ["config", "user.email", "szz-benchmark@example.com"])
    run_git(repo_dir, ["config", "core.autocrlf", "false"])
    run_git(repo_dir, ["config", "core.filemode", "false"])
    run_git(repo_dir, ["config", "i18n.commitEncoding", "utf-8"])
    run_git(repo_dir, ["config", "i18n.logOutputEncoding", "utf-8"])


_AUTHOR_RE = re.compile(r"^\s*(?P<name>.*?)\s*<(?P<email>[^<>]+)>\s*$")


def parse_author(author: str | None) -> tuple[str, str]:
    if not author:
        return "SZZ Benchmark", "szz-benchmark@example.com"
    match = _AUTHOR_RE.match(author)
    if not match:
        return author, "szz-benchmark@example.com"
    return match.group("name"), match.group("email")


def commit_all(repo_dir: Path, *, message: str, author: str | None, date: str | None) -> str:
    run_git(repo_dir, ["add", "-A"])
    status = run_git(repo_dir, ["status", "--porcelain"]).stdout.strip()
    if not status:
        raise GitError("commit would be empty")
    name, email = parse_author(author)
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = name
    env["GIT_AUTHOR_EMAIL"] = email
    env["GIT_COMMITTER_NAME"] = name
    env["GIT_COMMITTER_EMAIL"] = email
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    run_git(repo_dir, ["commit", "-m", message], env=env)
    return run_git(repo_dir, ["rev-parse", "HEAD"]).stdout.strip()


def git_show(repo_dir: Path, revision: str, path: str) -> str:
    return run_git(repo_dir, ["show", f"{revision}:{path}"]).stdout


def git_message(repo_dir: Path, revision: str) -> str:
    return run_git(repo_dir, ["log", "-1", "--pretty=%s", revision]).stdout.strip()


def git_parent(repo_dir: Path, revision: str) -> str | None:
    try:
        return run_git(repo_dir, ["rev-parse", f"{revision}^"]).stdout.strip()
    except GitError:
        return None


def git_hash_exists(repo_dir: Path, revision: str) -> bool:
    try:
        run_git(repo_dir, ["cat-file", "-e", f"{revision}^{{commit}}"])
        return True
    except GitError:
        return False


def git_blame_line(repo_dir: Path, revision: str, path: str, line_number: int) -> str:
    out = run_git(repo_dir, ["blame", "--porcelain", "-L", f"{line_number},{line_number}", revision, "--", path]).stdout.strip()
    if not out:
        return ""
    return out.splitlines()[0].split()[0].lstrip("^")
