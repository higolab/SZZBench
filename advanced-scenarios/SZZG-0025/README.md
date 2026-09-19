# SZZG-0025: Clone origin versus copied direct BIC

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate clone origin versus copied direct bic and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create original sanitizer
c1: introduce bug in original sanitizer
c2: copy sanitizer into admin module
c3: fix copied sanitizer only
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: clone, copy_file, origin_bic_policy
- Operation types: copy_file, replace, write_file
- Expected SZZ policy is defined in `expected_szz`.

## Expected BICs

```text
c2
```

(`c1` is the origin, not the answer — see [Expected SZZ result](#expected-szz-result).)

## Evaluation points

- Whether SZZ identifies the expected BIC set.
- Whether structural or contextual history is handled according to the scenario factors.
- Whether the expected_szz evaluation policy is applied correctly.

---

## Files

```text
SZZG-0025/
|-- scenario.graph.yml
`-- README.md
```

## Expected SZZ result

- Required: `c2` — the commit that copied the faulty sanitizer into `AdminSanitizer.java`, the instance the
  fix repairs. Under the [direct/origin contract](../../docs/decisions/origin-direct-contract.md) D4, the
  copying commit is the direct BIC of the instance it creates.
- Related origin: `c1` — it made the source sanitizer faulty, and the copy inherited that. Reporting it is a
  false positive under the default variant and accepted with credit 0.5 under `origin-aware` (D2, D3).
- Bug-fixing commit: `c3`.

Plain blame on the line the fix deletes returns `c2`, so the default oracle is within a blame-based tool's
reach; what the scenario tests is whether the tool stops there or walks back to `c1` and reports it as well.
