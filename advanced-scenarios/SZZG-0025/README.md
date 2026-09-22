# SZZG-0025: Clone origin versus copied direct BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `clone`, `copy-propagation`, `origin-bic-policy` |
| oracle | default: `exact_set`; required `c2`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `c2`; acceptable `c1` (credit 0.5) · BFC `c3` |
| graph features | operation `copy_file`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method reports the commit that copied a fault into the fixed file, rather than
the commit that created the fault elsewhere.

## Expected history

```text
c0: create original sanitizer
c1: introduce bug in original sanitizer
c2: copy sanitizer into admin module
c3: fix copied sanitizer only
```

## Expected BICs

```text
c2
```

(`c1` is the origin, not the answer — see [Expected SZZ result](#expected-szz-result).)

## Expected SZZ result

- Required: `c2` — the commit that copied the faulty sanitizer into `AdminSanitizer.java`, the instance the
  fix repairs. Under the [direct/origin contract](../../docs/decisions/origin-direct-contract.md) D4, the
  copying commit is the direct BIC of the instance it creates.
- Related origin: `c1` — it made the source sanitizer faulty, and the copy inherited that. Reporting it is a
  false positive under the default variant and accepted with credit 0.5 under `origin-aware` (D2, D3).
- Bug-fixing commit: `c3`.

Plain blame on the line the fix deletes returns `c2`, so the default oracle is within a blame-based tool's
reach; what the scenario tests is whether the tool stops there or walks back to `c1` and reports it as well.
