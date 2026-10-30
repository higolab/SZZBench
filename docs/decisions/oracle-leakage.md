# Decision: what the generated repositories may reveal about the oracle (issues #8, #9)

Status: **applied** (2026-09-18). This document states what SZZBench guarantees
about oracle leakage, what it deliberately does not guarantee, and how both are
checked.

## 1. Threat model

An SZZ tool is given a **generated repository** and the **bug-fixing commit**,
and must report the bug-introducing commit(s). Everything inside that
repository — commit messages, author names, author and committer dates, file
contents, file paths, refs — is input the tool may read. Anything in there that
identifies a commit's role in the oracle is a leak, because it lets a tool score
well without analysing the change.

Scenario YAML, READMEs, `index.yml` and this repository's directory names are
**not** part of the threat model: a tool under evaluation is given the generated
repository, not the benchmark source. Section 5 says what follows from that.

## 2. Commit messages

A commit message describes the change from the point of view of the developer
who made it. The developer who introduces a bug does not know they are
introducing one, so their message reads like any other intentional change:

```text
Make the range check exclusive              (a bug-introducing commit)
Cut the 1.0 release branch                  (a branch point)
Extract the free-shipping predicate         (a refactoring)
Accept the range bounds again               (the fix)
```

Rules:

- **No logical id anywhere in the message.** `c1: ...`, `WI-001 c2: ...`,
  `Rel1: ...` and `suspected c0` are scenario bookkeeping, not commit messages
  (`W411` / `GW411`). Issue and work-item identifiers are legitimate and stay:
  `ISSUE-482`, `PAY-314`, `WI-001` are what a real project writes.
- **No role words in a non-fixing commit**: `BIC`, `BFC`, `bug-introducing`,
  `introduce ... bug` — including hyphenated variants such as
  `introduce context-sensitive bug` — `with ... bug`, `buggy`, `faulty`,
  `faulty statement`, `distractor`, `intermediate change`, `initial state`,
  `noise`, `unrelated`, `replay...`, `reintroduc...` (`W410` / `GW410`).
- **No operation lists.** `(replace src/main/java/example/Range.java)` describes
  the scenario schema, not the change.
- **Bug-fixing commits keep natural fix wording.** The BFC is an *input* to SZZ,
  not part of the answer, so "Accept the range bounds again" or an issue id in
  the fix message is legitimate evidence, and several scenarios exist precisely
  to test whether a tool uses it.

## 3. Author and date

Both are assigned **deterministically from (scenario id, commit index)** and
never from the role.

- **Normal suite**: written into the scenario files, and the generator takes
  them from there. When they were first written, authors came from an
  eight-name pool, with a 30% chance of repeating the previous commit's author
  so that runs by one developer still occur, and dates were weekday timestamps
  between 2023 and mid-2025 with gaps of one to nine days and working-hour
  times. Scenarios added since choose their own, and 21 of them (SZZ-0195
  onwards) also name authors from the six-name pool the graph suite's
  generator uses (`gitutils.DEFAULT_AUTHOR_POOL`). On 2026-10-10 the 133
  classic files name fourteen authors: the eight with 51–73 commits each and
  the six with 6–12. A classic commit without an `author` would be given one
  from the six-name pool, as a graph commit is; none is today. The author
  checks of §7 measure the authors the generated repository will have
  (`gitutils.resolved_commit_authors`), not either pool.
- **Graph suite**: not written into the scenario files; the generator supplies
  them (`gitutils.deterministic_author`, `gitutils.deterministic_date`), with a
  per-scenario base date so repositories do not all start on the same day.
- An explicit `author`, `date`, `author_date`, `committer_date` or
  `repository.base_date` always wins, and the first commit sits exactly on the
  base date. Scenarios that need a specific timeline — rebases, where the author
  date precedes the committer date — set it explicitly.

A scenario that **pins any timestamp** keeps the plain one-day-per-commit
schedule for the commits it leaves to the generator. Spreading only some of them
over the irregular gaps would place them after the pinned ones; four rebase
scenarios briefly ended up with a parent committed a year after its child that
way, and `verify-graph` now rejects that with `GE630`.

Dates remain strictly increasing in the commit index, so a commit is always
newer than its parents. A date therefore still tells a tool the commit's
*position*, which the commit graph already shows; it no longer tells it the
*role*.

## 4. File contents and paths

The repository must not contain prose about its own oracle. Removed examples:

| was | now |
|---|---|
| `docs/main-note.md`: "This note is unrelated to the range boundary bug." | "Release checklist for the upcoming minor version." |
| `docs/ranking-distractor.md`: "This commit is a ranking distractor for top-k SZZ evaluation." | `docs/range-service-notes.md`: "Notes on the range service configuration." |
| `docs/boundary-test-note.md`: "... but the implementation is still buggy here." | "Boundary cases should be covered by tests." |
| `pom.xml`: `<artifactId>dependency-bic</artifactId>` | `<artifactId>range-adapter</artifactId>` |
| `// fixed cloned logic` | `// cloned logic, reviewed` |

Paths follow the same rule (`docs/main-after-fix.md` → `docs/main-development.md`),
and `commit_generator` no longer writes the generated commit's id into the file
it touches.

## 5. Deliberate non-goals

- **Scenario and repository names describe the scenario.**
  `SZZ-0081-formatting-after-bic` is the directory a repository is generated
  into. It names the *scenario design*, not which commit is the answer, and the
  scenario id in it is public benchmark identity that no renaming can hide. A
  protocol that wants to withhold it should hand the tool the repository
  contents under a neutral path; the benchmark does not pretend to hide it.
- **A fix describes what it fixes.** Any bug-fixing commit necessarily names the
  entity it repairs, in its diff if not in its message. Scenarios in category G7
  therefore claim that *line-based blame baselines fail while message or issue
  evidence succeeds*, not that the code carries no clue; each one records its own
  alternative code route under `scenario_design.code_evidence_limitation`.
- **Behaviour is evidence.** Running the tests or the code distinguishes commits.
  That is analysis, not leakage.

## 6. How predictions may name a commit

`evaluate --reference-format` makes the accepted prediction format explicit:

| value | accepts | for |
|---|---|---|
| `auto` (default) | logical ids, full hashes, unique short hashes | existing prediction files |
| `hash` | full hashes and unique prefixes of at least 7 characters | tool runs — a tool that reads the repository can only produce hashes |
| `logical` | scenario ids such as `c1` | adapters, fixtures and tests, which know the scenario |

Rejected references are counted as unknown predictions rather than silently
dropped. Reported tool results should state which format they used; `hash` is
the honest setting for a tool run, because accepting logical ids lets a tool
that recognises the benchmark answer in the scenario's own vocabulary.

## 7. How this is checked

- `validate --lint` / `validate-graph --lint`: `W410`/`W411`/`W412` and
  `GW410`/`GW411`/`GW412` (see [validation.md](../validation.md)); and
  `W413`/`GW413` (issue #43), which warns when some author's set of commits is
  exactly a multi-commit oracle — the coincidence of the author rotation that
  twice let a naive rule solve a discriminating scenario (SZZG-0118, SZZG-0028)
  and that the `meta.tier` check only catches for discriminating scenarios. The
  one-commit form is reported as `I413`/`GI413` and left alone. When the lint
  fired on the first sweep (SZZG-0007, SZZG-0039), the repair was an explicit
  `author` on one of the required commits.
- `tests/test_no_oracle_leakage.py` runs over the shipped scenarios: no message
  or written file discloses a role, every commit resolves to an author and a
  date, no author holds more than 45% of any role, and two metadata-only
  predictors are scored. **The message predictor uses its own vocabulary, not
  the lint's pattern.** The first version of this guard reused the lint regex
  and therefore reported zero leaks for six scenarios whose messages the lint
  could not see (`Introduce context-sensitive bug` — the lint required the word
  "bug" within three *unhyphenated* words of "introduce"; `Introduce ambiguous
  faulty statement` — no "bug" at all; `WI-001 c2: ...` — the prefix check was
  anchored). A guard measured with the instrument it is guarding proves nothing.
- `verify-graph`, and therefore `generate-graph`, rejects a commit dated before
  one of its parents (`GE630`) and warns when an author date is later than its
  committer date (`GW631`).

Measured on the suite as shipped:

| predictor | before | after |
|---|---|---|
| "report the commits written by Bob" (one author fixed across the suite) | 70/101 normal (69%) | best author 11/249 (4.4%; 11/206 = 5.3% when first measured) |
| "report the non-BFC commits whose message announces a bug" | 51/101 normal, 30/105 graph | 0/249 |

The residual is at chance, and "chance" is measured rather than asserted
(issue #36). The statistic — the best single author fixed across the suite — is
a maximum over authors, so its chance level is the distribution of that maximum
when the labels carry no information: shuffle the author labels *inside* each
scenario (keeping every scenario's multiset of authors and its commit count),
recompute the maximum, repeat. On the 249 scenarios with a commit-level oracle
(2026-09-21, 1000 draws): null mean 13.8, median 14, 95th percentile 17, maximum
22; the observed 11 is *below* the null mean, with p(null ≥ observed) = 0.99 —
the author carries no information about the oracle. The guard in
`tests/test_no_oracle_leakage.py` asserts observed ≤ the null's 95th percentile
(500 draws, fixed seed) instead of the hand-picked 10% it used until then; that
constant (20.6 of 206) was below the null's maximum (21) on the suite it was
written against, so a clean suite could have failed it. Any further
metadata-only guard (dates, message length, e-mail domain) should be calibrated
the same way: shuffle the field under test within each scenario and compare the
best rule against the resulting distribution.
