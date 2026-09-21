# SZZG-0061: Cherry-picked BIC appears as duplicate commits on two branches

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `cherry-pick`, `duplicate-patch`, `non-linear-history` |
| oracle | default: `exact_set`; required `c2`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `c2`; acceptable `c1` (credit 0.5) · BFC `c3` |
| graph features | 2 branches; cherry-pick `c2`; 2 BICs; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate cherry-picked bic appears as duplicate commits on two branches and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create status mapper
c1: introduce wrong error status on release branch
c2: cherry-pick wrong error status onto main
c3: fix wrong error status on main
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: cherry_pick, duplicate_patch, non_linear_history
- Operation types: replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c2
```

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0061/
|-- scenario.graph.yml
`-- README.md
```

## Expected SZZ result

- Required: `c2` — the copy of the change that lives in `main`, the history the fix belongs to (contract D4).
- Related origin: `c1` — the `release` commit it was picked from. `c1` is **not** an ancestor of the fix, so
  reporting it names a commit outside the evaluated history; it is accepted with credit 0.5 under
  `origin-aware` (D2, D3).
- Bug-fixing commit: `c3`.

The cherry-pick is manual: the generated commit carries no `(cherry picked from …)` trailer, so the lineage is
declared with `cherry_pick_of` in the scenario rather than being recoverable from the commit message.
