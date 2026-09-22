# SZZG-0023: Rebase with copy propagation

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `branch`, `rebase`, `copy-propagation`, `duplicate-code`, `direct-bic`, `origin-bic` |
| oracle | default: `exact_set`; required `r2`; related origins `r1`, `f2`, `f1` · `origin-aware`: `relaxed_with_related`; required `r2`; acceptable `r1` (credit 0.5), `f2` (credit 0.5), `f1` (credit 0.5) · BFC `c3` |
| graph features | 2 branches; rebase `r1`, `r2`; operation `apply_patch_from`; 4 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

A feature branch makes the score band exclusive (`f1`) and then copies the same
comparison into a second class for draft submissions (`f2`). Both commits are
rebased onto `main` as `r1` and `r2`. The bug report is about the draft band, so
the fix repairs the **copied** instance: the direct BIC is the commit that
created the copy (`r2`), while the rebased original (`r1`, same comparison in
`ScoreBand`) and the two pre-rebase commits are origins.

## Commit graph (as generated)

`git log --all --graph`, with the logical ids in place of the hashes:

```text
* c3 (HEAD -> main) Accept the draft band bounds again so 0 and 100 stay valid draft scores
* r2 Add DraftScoreBand for draft submissions
* r1 Require review scores strictly inside the accepted band
| * f2 (feature) Add DraftScoreBand for draft submissions
| * f1 Require review scores strictly inside the accepted band
|/
* c0 Add ScoreBand with the accepted review score range
```

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | – | `initial` | Add ScoreBand with the accepted review score range |
| `f1` | `feature` | c0 | `origin_bug_introducing` | Require review scores strictly inside the accepted band |
| `f2` | `feature` | f1 | `origin_bug_propagating` | Add DraftScoreBand for draft submissions |
| `r1` | `main` | c0 | `bug_introducing` | *(subject and author date inherited from `f1`)* |
| `r2` | `main` | r1 | `bug_introducing` | *(subject and author date inherited from `f2`)* |
| `c3` | `main` | r2 | `bug_fixing` | Accept the draft band bounds again so 0 and 100 stay valid draft scores |

Refs after generation (`git for-each-ref`): `refs/heads/main` → `c3`,
`refs/heads/feature` → `f2`.

### Rebase fidelity (measured)

`r1` and `r2` declare no message of their own. With `inherit_message` they
carry the subjects of `f1` and `f2`, and with `inherit_author_date` their author
dates are those of `f1` (`2024-01-02T10:00:00Z`) and `f2`
(`2024-01-03T10:00:00Z`) while their committer dates are the rebase dates
(`2024-01-04` / `2024-01-05`) — the author-date-before-committer-date signature
of a real rebase. Both are generated with `apply_patch_from`, and
`git show --format= --no-renames -U0` of `f1`/`r1` and of `f2`/`r2` produces
identical patches (only the blob index lines differ).

### Are the pre-rebase commits reachable? Yes, on purpose

The `feature` branch is **kept**, so `f1` and `f2` stay reachable
(`git rev-list --all` lists all six commits). This is a deliberate decision, not
an omission:

* it models the common real case — a GitHub *Rebase and merge*, or any rebase
  whose source branch was not deleted — in which the pre-rebase commits are
  still in the repository;
* it is what makes the `related_but_not_correct` entries `f1` and `f2`
  meaningful: a tool can actually see and report them, and must not;
* SZZG-0072 is the counterpart where `graph.ref_lifecycle.delete_branches`
  removes the branch and the pre-rebase commits become unreachable. Keeping both
  variants in the suite is the point; per the decision record
  (`docs/decisions/origin-direct-contract.md`, D8) reachability is a controlled
  scenario property that does not change the oracle.

### Category placement

`category_code` stays **G2** (clone, copy propagation, origin vs direct BIC).
The mechanism is a rebase, so a G5 placement would also be defensible, and the
scenario is listed under the G5 design question in GitHub issue 4. The
discriminating property, however, is which of the two textually identical
comparisons the fix belongs to — that is the G2 question; the rebase only adds
two more origin candidates (`f1`, `f2`) next to the in-history origin `r1`. If
the suite ever reclassifies by mechanism rather than by tested property, this
scenario moves to G5 together with the other rebase scenarios; the change was
not made here because the task keeps `category_code` fixed.

## Expected SZZ result

```text
Expected BFC: c3
Required BIC: r2                   (direct: the rebased copy commit)
Related but not correct: r1, f1, f2 (origins)
```

Unchanged by this repair.

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`    return score > LOWEST_DRAFT_SCORE && score < HIGHEST_DRAFT_SCORE;` (line 8
of `src/main/java/example/DraftScoreBand.java`). `git blame` at `c3^` on that
line returns **`r2`**, the required BIC — the outcome is **hit**. `-M`, `-C -C`
and `-w` also return `r2`; the copy detection of `-C -C` does not jump to the
`ScoreBand` instance. Generation reports `GI703`.

## What a tool must do to pass

Report exactly `{r2}`. The three ways to fail are all "one step too far":

* `r1` — the same comparison exists in `ScoreBand` and is still faulty after
  the fix; a tool that searches for the first commit that ever wrote this text
  in the history reports `r1`;
* `f1` / `f2` — the pre-rebase commits are reachable through `feature` and have
  the same subjects and author dates as `r1`/`r2`, so patch-id or subject
  matching finds them.

All three are `related_but_not_correct`, i.e. false positives under
`exact_set`.

## Behaviour check (measured)

All six commit snapshots compile with `javac` (JDK 25): 0 failures out of 6.

`ScoreBand.accepts(int)` and (from `f2`/`r2` on) `DraftScoreBand.accepts(int)`
were probed over `{Integer.MIN_VALUE, MIN_VALUE+1, -1, 0, 1, 99, 100, 101,
MAX_VALUE-1, MAX_VALUE}` (10 inputs: both `int` limits and both boundary
constants, ±1).

* `r2` (BIC) differs from `c0` on **2 of 10** shared probes:
  `ScoreBand.accepts(0)` and `ScoreBand.accepts(100)` (inherited from `r1`),
  and it adds 10 probes for `DraftScoreBand.accepts`, which rejects `0` and
  `100` as well.
* `r1` reproduces `f1` and `r2` reproduces `f2` exactly (0 differences on all
  shared probes) — the replays are behaviour-identical to their sources.
* `c3` (BFC) fixes the copy: it differs from `r2` on exactly
  `DraftScoreBand.accepts(0)` and `DraftScoreBand.accepts(100)`.
* **Deviation, by design:** `c3` does *not* agree with `c0` on all shared
  probes. It still differs on `ScoreBand.accepts(0)` and
  `ScoreBand.accepts(100)`, because the fix is scoped to the draft band. That is
  the scenario's core property: if the BFC also repaired `ScoreBand`, `r1` would
  be a second direct BIC of the same fix and the origin-vs-direct distinction
  would disappear.
