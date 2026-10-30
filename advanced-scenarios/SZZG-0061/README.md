# SZZG-0061: Cherry-picked BIC appears as duplicate commits on two branches

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `cherry-pick`, `duplicate-patch`, `non-linear-history` |
| oracle | default: `exact_set`; required `c2`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `c2`; acceptable `c1` (credit 0.5) · BFC `c3` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 branches; cherry-pick `c2`; 2 BICs; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports the copy of a cherry-picked commit that is in the fix's own
history.

## Expected history

```text
c0: create status mapper
c1: introduce wrong error status on release branch
c2: cherry-pick wrong error status onto main
c3: fix wrong error status on main
```

## Expected SZZ result

- Required: `c2` — the copy of the change that lives in `main`, the history the fix belongs to (contract D4).
- Related origin: `c1` — the `release` commit it was picked from. `c1` is **not** an ancestor of the fix, so
  reporting it names a commit outside the evaluated history; it is accepted with credit 0.5 under
  `origin-aware` (D2, D3).
- Bug-fixing commit: `c3`.

The cherry-pick is manual: the generated commit carries no `(cherry picked from …)` trailer, so the lineage is
declared with `cherry_pick_of` in the scenario rather than being recoverable from the commit message.
