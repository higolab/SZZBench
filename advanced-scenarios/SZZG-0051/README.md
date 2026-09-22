# SZZG-0051: Backport introduces release-specific bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `backport`, `wrong-constant` |
| oracle | `exact_set`; required `r1` · BFC `r2` |
| graph features | 2 branches; backport `r1` |
<!-- /szzbench:header -->

## Purpose

`c1` adds a retention policy on `main` — a source change, not a fix. `r1`
backports it to `release` and, in the same commit, rewrites the retention
period: the message announces the 30-day retention and the code says `return
3;`. The release-specific bug is fixed on `release` by `r2`; `main` never has it.
The BIC is the backport adaptation `r1`, not the main-line change it adapts.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 4 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* bc6f446  2025-06-16  Keep backups for 30 days on release, not 3                             <- BFC (r2, release)
* 1798b8f  2025-06-09  Backport the retention policy to release and set the 30-day retention  <- BIC (r1, release; backport_of c1)
| * 3a91953  2025-06-02  Add the main retention policy                                        (c1, main; source change)
|/
* a4c716e  2025-05-30  Add the backup retention period                                        (c0; Retention.days() = 30)
```

## Expected BIC / BFC

- BIC: `r1` (`exact_set`, `required: [r1]`)
- BFC: `r2`

## Measured behaviour and blame

| commit | `Retention.days()` | `RetentionPolicy.mode()` |
|---|---|---|
| `c0` | 30 | — |
| `c1` | 30 | `main` |
| `r1` | **3** | `release` |
| `r2` | 30 | `release` |

`r2` deletes one line (`return 3;`, line 6); blame at `r2^` returns `r1`
(verifier `GI703`).

## What a tool must do

Report `r1`. The `backport_of: c1` metadata and the shared subject line invite
a tool to blame `c1`, but `c1` touched only `RetentionPolicy.java`; the faulty
line was written on `release` by the adaptation itself.
