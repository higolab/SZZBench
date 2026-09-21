# Decision: tool-visible context lives inside the generated repository (issue #23)

Status: **decided 2026-09-21**, applied by SZZG-0130 and SZZG-0131.

## 1. Problem

Some SZZ methods use evidence beyond the diff: the bug report and its date (the
original "a commit after the report cannot have introduced it" heuristic), issue
text, work-item membership. Until now that evidence existed only in the scenario
YAML (`issues:`, `work_items:`), which an adapter can read but a tool that is
handed a repository cannot. A scenario about the report-date heuristic therefore
could not be built.

## 2. Decision

**The context a tool may use is committed into the generated repository as an
ordinary document**, written by an ordinary `write_file` operation of an ordinary
commit. Nothing is passed out of band.

- Location: `docs/issues/<ISSUE-ID>.md`.
- The document is what a reporter would write: a title, `Reported: <ISO 8601
  timestamp>`, and the symptom as observed. It says what is wrong, never why.
- It must not contain oracle labels, logical commit ids or role words. This is
  not a new rule: the leakage lint already scans every `write_file` /
  `replace.new` / `insert_after.content` text (`W412` / `GW412`, issue #8), so
  the same words that are forbidden in commit messages are forbidden here.
- The scenario's `issues:` entry stays the oracle-side record and gains two
  keys: `document` (the path written) and `reported_at` (the timestamp the
  document states). `GW470`/`GW471` check that the document is written by some
  commit and that its `Reported:` line names the same instant, so the two
  cannot drift. Both values go through the generator's timestamp parser, so
  `reported_at` may be quoted or unquoted in YAML (PyYAML turns the latter into
  a `datetime`) and either side may use `Z` or an offset; a value that is not a
  timestamp at all is `GW472`, never silence.
- The relation between `reported_at` and the commit dates is a controlled
  property of the scenario, so every commit that matters to it pins `date` (or
  `author_date` / `committer_date`).

## 3. Why in the repository, not a context file for adapters

An adapter-side context file would keep the history clean, but it needs an
interface every adapter must learn, and it makes the benchmark's answer depend
on which of two inputs a tool was given. A document in the repository is seen by
every tool the same way, including tools that read nothing but the repository,
and it is versioned with the history: the report exists from the commit that
recorded it onward, which is exactly what the date heuristic reasons about.

## 4. What the two first scenarios exercise

- SZZG-0130 — the report is filed between the BIC and a later behaviour-preserving
  rewrite; excluding commits after the report is the right move.
- SZZG-0131 — the direct BIC is a rebased commit whose committer date is after
  the report while its author date is before; excluding by committer date is the
  wrong move.
