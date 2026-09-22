# SZZG-0143: Divergent fixes on main and release for one BIC, with a branch-level oracle

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `branch`, `release-branch`, `single-bic`, `multi-bfc`, `divergent-fix`, `branch-level-oracle`, `formatting-noise`, `wrong-constant` |
| oracle | `exact_set`; required `c1`; related but not correct `r1`; known distractors `r1`, `c2` · BFCs `c3`, `r2` · branch-level: main → `c1` (BFC `c3`); release → `c1` (BFC `r2`) |
| defeats | `blame`, `shape` |
| graph features | 2 branches; 2 BFCs; `branch_level` oracle |
<!-- /szzbench:header -->

## Purpose

One commit introduces the fault, two commits fix it — one on `main`, one on
`release`, written independently with different text. The release branch also
re-wrapped the faulty line before fixing it, so the two fixes have different
histories behind them: blame from the main fix reaches the BIC, blame from the
release fix stops at the reformat. The scenario is the first whose
`expected_szz.branch_level` the evaluator reads: a tool run from each fix is
scored against that branch's required set, and a failure on either branch
fails the scenario (issue #22).

## Commit graph

```text
c0 ──► c1 ──► c2 ──► c3          main
        └──► r1 ──► r2           release

c0  Add the ticket validity check                               ttlMinutes * 60
c1  Express the ticket lifetime with the standard multiplier    ttlMinutes * 1000      <- BIC
r1  Cut the 2.1 release branch and wrap the long lines          line re-wrapped, value unchanged
c2  Document the validity check                                 Javadoc only
c3  Convert the ticket lifetime to seconds with a named constant  ttlMinutes * SECONDS_PER_MINUTE   <- BFC (main)
r2  Convert the ticket lifetime to seconds with TimeUnit        TimeUnit.MINUTES.toSeconds(ttlMinutes)  <- BFC (release)
```

`r2` is not a cherry-pick of `c3`: the two fixes share no text and no
commit metadata; each developer fixed the unit on their own branch.

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`); `r1` is `related_but_not_correct` and a known distractor
  together with `c2`
- BFCs: `c3` (main) and `r2` (release), both `complete_fix`
- **Branch-level oracle**: `main` → BFC `c3`, required `{c1}`; `release` → BFC `r2`, required `{c1}`

A prediction whose `fix_commit` resolves to `c3` is scored against the `main`
entry, one whose `fix_commit` resolves to `r2` against the `release` entry; a
prediction without `fix_commit` counts for both. The scenario passes only when
the commit-level oracle passes **and** every branch passes
(`docs/evaluation-policies.md`, section 1.5).

## Measured behaviour and blame

`isValid(4000, 1000, 10)` — a ticket issued 3000 seconds ago with a
ten-minute lifetime — at each commit (`tests/test_branch_level.py`):

| commit | result |
|---|---|
| `c0` | false |
| `c1` | **true** |
| `r1` | **true** |
| `c2` | **true** |
| `c3` | false |
| `r2` | false |

- `c3` deletes `return nowSeconds - issuedAtSeconds <= ttlMinutes * 1000;`; `git blame` at `c3^`
  attributes it to **`c1`**.
- `r2` deletes `        <= ttlMinutes * 1000;`, the second line of the expression `r1` wrapped; `git blame`
  at `r2^` attributes it to **`r1`**, the reformat — and so does `git blame -w`, because `r1` did not
  change whitespace inside a line, it split one line into two, so the deleted line has no counterpart in
  `c1`'s version. The declared fault statement is the original one-line form and is not present at `r2^`
  (`GI701`, declared by `formatting-noise`).

## What a tool must do

Report `{c1}` from **both** fixes. From `c3` plain blame already does it. From
`r2` blame answers `r1` under every variant, so a tool has to recognise `r1` as
a formatting-only commit — its diff of `Ticket.java` changes no token, only the
line break — and step past it to the commit that last changed the tokens,
`c1`. A tool that reports `r1` for the release fix and `c1` for the main fix
fails the `release` branch and therefore the scenario, even though its
main-line answer is right — and the report says which branch failed.
