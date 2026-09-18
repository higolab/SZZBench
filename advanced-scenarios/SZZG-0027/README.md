# SZZG-0027: Clone divergence before fixing one clone

## Source

- Category: Clone propagation scenarios

## Purpose

Evaluate clone divergence before fixing one clone and whether SZZ identifies the expected bug-introducing commit set.

## Expected history

```text
c0: create base permission check
c1: introduce permissive delete check
c2: clone policy to group policy
c3: diverge copied clone by renaming parameters
c4: fix copied clone after divergence
```

## Why this needs `scenario.graph.yml`

This history requires graph-aware scenario semantics that are difficult to express with the normal `scenario.yml` schema.

## Required graph-schema features

- Factors: clone, clone_divergence, ambiguous_blame
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

## Draft status

This scenario is a draft for the `scenario.graph.yml` schema and is intended for graph-aware generation and verification.

## Files

```text
SZZG-0027/
|-- scenario.graph.yml
`-- README.md
```

## Expected SZZ result

- Required: `c2` — the commit that cloned the faulty policy into `GroupPolicy.java`, the instance the fix
  repairs (contract D4).
- Related origin: `c1` — it made the source policy faulty (D2); accepted with credit 0.5 under `origin-aware`.
- Related but not correct: `c3` — it renames the parameter in the fixed file and changes no behaviour, so it
  is never a BIC (D5) even though it is the last commit to touch the line the fix deletes.
- Bug-fixing commit: `c4`.

`c3` is what makes this scenario worth running: plain blame at `c4^` returns `c3`, a rename.
