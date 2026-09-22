# SZZG-0100: Unrelated commits mixed in the same issue

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `work-item`, `issue-evidence` |
| oracle | `exact_set`; required `c1`; related but not correct `c2`, `c3` · BFC `c4` |
| graph features | `issues`; `work_items` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ picks the one commit of a work item that introduced the defect when
**every** commit of that work item carries the same identifier. Collecting the issue's
commits is not enough; three of the four are not the cause.

Before this repair, `ISSUE-10` appeared in no commit message at all (only as the name of a
docs file), so the work-item linkage existed solely in the YAML, and that docs file said
"This note is unrelated to the boundary defect.", which leaked the oracle (issue #4).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3 ──► c4          (branch: main, linear)

c0  Add the range service                                        (RangeService.java, inclusive bounds)
c1  ISSUE-10 use an exclusive interval in RangeService.contains  <- BIC
c2  ISSUE-10 rename the normalize parameter to rawValue          unrelated to the defect, same ticket
c3  ISSUE-10 document the range validation rules                 adds docs/range-validation.md
c4  ISSUE-10 include the interval bounds in contains() again     <- BFC
```

All four commits after the initial one carry `ISSUE-10` in their message
(`git log --grep=ISSUE-10 --oneline` returns 4 commits), which is what the `work_items`
block claims. The documentation file now contains real documentation and no longer names
the defect or the fix.

## Expected BIC / BFC

- BIC: `c1` (`expected_szz.commit_level.required = [c1]`, policy `exact_set`)
- BFC: `c4`
- `related_but_not_correct`: `c2`, `c3` — the other non-fix commits of the same work item

## Measured plain-blame outcome at BFC^

`BFC^` is `c3`. The BFC deletes exactly one line:

```text
src/main/java/example/RangeService.java:9  "    return value > min && value < max;"  ->  c1
```

Outcome: **exact**. `git blame` at `BFC^` reaches `c1`, the required BIC (`GI703`).
The difficulty of this scenario is not the blame step but the issue linkage: a tool that
answers "the commits of the fix's issue" returns `{c1, c2, c3}` and over-reports two
commits.

## What a tool must do to pass

- Report exactly `{c1}`.
- Not widen the answer to the other commits that reference `ISSUE-10`: `c2` only renames a
  parameter of `normalize`, `c3` only adds a Markdown file (neither can change `contains`).
- Not use the documentation file as a shortcut: it describes the service without stating
  whether the bounds are inclusive.

## Behaviour check (measured)

`RangeService.contains(int,int,int)`, `normalize(int)` and `isEnabled()` were run on 113
probes: values `{MIN_VALUE, MIN_VALUE+1, -6, -5, -4, -1, 0, 1, 6, 7, 8, 9, 10, 11, MAX_VALUE-1, MAX_VALUE}`
against the intervals `(0,10)`, `(-5,5)`, `(7,7)`, `(MIN_VALUE,MAX_VALUE)`, `(MIN_VALUE,0)`,
`(0,MAX_VALUE)`, plus `normalize` on the same 16 values and `isEnabled()`.

- `c1` (BIC) differs from `c0` on the 10 boundary inputs of `contains`.
- `c2` and `c3` are **identical to `c1`** on all 113 probes (the rename and the docs file
  change no behaviour).
- `c4` (BFC) is **identical to `c0`** on all 113 probes.
