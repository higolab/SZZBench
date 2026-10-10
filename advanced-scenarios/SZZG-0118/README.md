# SZZG-0118: A reduced copy of a helper, and a later call routed through it

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `clone`, `origin-and-direct-bic`, `caller-callee-interaction`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
| graph features | operation `copy_file`; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. It is the
third instance of the *callee* kind — after
[SZZ-0191](../../scenarios/SZZ-0191/README.md) (the called method's body
changed) and [SZZ-0196](../../scenarios/SZZ-0196/README.md) (which overload the
call selects) — and here the callee is a **copy** of another class, so the step
a tool has to take is resolving the call into the copied file.

## Commit structure

```text
c0  Add the label normalizer and the tag matcher       normalize() trims and lower-cases
c1  Copy the normalizer for already lower-cased imports  ImportNormalizer.normalize() only trims  <- BIC
c2  Say which normalizer imports use                   class comment only
c3  Match a tag typed by the user against an imported one  adds matchesTypedTag() -> ImportNormalizer  <- BIC
c4  Normalize a typed tag the way stored tags are normalized  -> Normalizer                        <- BFC
```

`c1` adds a class and touches nothing that existed before it; dropping the
lower-casing is correct for the import pipeline, whose labels arrive lower-cased
already. `c3` is the first commit to send user input through that class, so a
tag typed as `HOTFIX` stops matching the tag `hotfix`.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`exact_set`, `required: [c1, c3]`)
- BFC: `c4`

## Measured behaviour (from the generated repository)

Every public method of the three classes, over a grid of strings. Per commit,
how many **shared** probe keys change value, and how many appear:

```text
c0  Add the label normalizer and the tag matcher       56 probes
c1  Copy the normalizer for already lower-cased imports  changed 0, added 7   <- adds a class, moves nothing
c2  Say which normalizer imports use                   changed 0, added 0
c3  Match a tag typed by the user against an imported one  changed 0, added 49
c4  Normalize a typed tag the way stored tags are normalized  changed 5
```

The fix makes the new method consistent with the old one: after `c4`,
`matchesTypedTag` agrees with `matchesStoredTag` on **all 49** probed argument
pairs, with none disagreeing.

**Both commits are necessary, measured rather than argued.** Making the copy
faithful on top of `c3` — the tree in which the new call exists but the reduced
copy does not — reproduces the fixed behaviour on **all 98** probe keys, with
zero differences.

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return ImportNormalizer.normalize(typed).equals(tag);"   plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns `{c3}` — half the answer — and `c1` is not reachable from the
deleted line by any blame variant.

Blame is, however, reliable *inside* the copy. The copy's own reduced line is
attributed to `c1` by every variant, copy detection included:

```text
"return raw.trim();" in ImportNormalizer.java at BFC^
   plain -> c1   -w -> c1   -C -> c1   -C -C -> c1   -w -C -C -> c1
```

The line was modified in the copying commit rather than carried over unchanged,
so `-C` has nothing to trace back to `Normalizer`. What this scenario isolates
is therefore exactly one step: resolving the call in the fixed line into the
copied class. A tool that takes it can then blame correctly; a tool that does
not never sees `c1` at all.

## What a tool must do to pass

Report exactly `{c1, c3}`. That means treating a commit that only *adds* a
class as a possible bug-introducing commit, and reaching it through the call in
the line the fix repairs.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.
