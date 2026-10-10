# SZZG-0122: Rebased feature branch deleted after the rebase (twin of SZZG-0057)

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `old-base`, `unrelated-main-changes`, `origin-vs-direct` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `m1`, `m2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `m1`, `m2` · BFC `c3` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; rebase `r1`; ref lifecycle; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

The same commits as [SZZG-0057](../SZZG-0057/README.md), with one difference in
the repository a tool receives: after the rebase the pre-rebase branch
`feature` is deleted (`graph.ref_lifecycle.delete_branches`). The origin `f1`
keeps a valid hash but is reachable from no ref. The oracle is identical in
both twins; the pair separates tools that walk from refs from tools that walk
every object.

## Commit structure (generated)

```text
* eddf3f3  Accept the range bounds again        <- BFC (c3)
* 4a3aa06  Make the range check exclusive       <- BIC (r1), rebase_of f1
* 2067f93  Add the second main note             (m2)
* 1cdb4e6  Add the first main note              (m1)
* e93ce02  Add the range check                  (c0)
```

These are **the same commit objects as SZZG-0057's**, hash for hash: every
commit pins the author, author date and committer date the generator resolved
for SZZG-0057, so a metadata-only rule cannot tell the twins apart.
`tests/test_twins_and_transitions.py` generates both and asserts the identity.
`git for-each-ref` lists only `main`. The commit `f1` still exists as an object
(`git cat-file -t` answers `commit`) but `git branch -a --contains <f1>` is empty:
`git log --all` shows one copy of the faulty change here and two in SZZG-0057.

## Expected BIC / BFC

- BIC: `r1` (`exact_set`, `required: [r1]`) — the replay in the fix's history
- `related_origins`: `f1` — the pre-rebase original; a false positive under the
  default variant, half credit under `origin-aware` (contract D8: reachability
  is a controlled property of the repository, not a change to the oracle)
- `related_but_not_correct`: `m1`, `m2`
- BFC: `c3`

## Measured blame outcome at BFC^

Blaming the line `c3` deletes returns `r1`; the verifier reports `GI703`. Plain
blame solves both twins.

## What a tool must do

Report `r1` and behave exactly as on SZZG-0057. A tool whose answer differs
between the twins is reading ref reachability: here it cannot reach `f1` at
all, there it can and must still not prefer it.
