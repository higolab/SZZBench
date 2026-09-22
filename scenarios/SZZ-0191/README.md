# SZZ-0191: The other bug-introducing commit is in the method the fixed line calls

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `caller-callee-interaction`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario whose unreachable commit sits behind a **call**:
the fix repairs a caller, and the commit that made the caller wrong is the one
that changed the callee.

## Commit structure

```text
c0  Add the tag store with a normalizing lookup   known() trims and lower-cases
c1  Look the tag up without rebuilding the key    known() compares the raw tag    <- BIC
c2  Describe the accepted tags                    class comment only (distractor)
c3  Accept a tag typed by the user                adds knownFromInput(typed)      <- BIC
c4  Normalize the typed tag before looking it up  known(typed.trim().toLowerCase())  <- BFC
```

`c1` changes what `known()` accepts for input that is not already normalized;
the only caller at that point, `knownFromMenu`, passes normalized values, so no
caller in the repository is affected. `c3` adds a caller that passes raw user
input, and only then is a tag such as `" Release "` rejected.

## Expected BIC / BFC

- BICs: `c1` and `c3`; BFC: `c4`

Without `c1` the lookup would still normalize and the new caller would be
correct; without `c3` nothing passes raw input.

## Measured blame outcome at BFC^

```text
"return known(typed);"    plain -> c3    -w -> c3    -w -C -C -> c3
```

`c1` is in `known()`, which the fix does not edit, so no blame variant reaches
it.

## Baseline outcome (measured)

No declared baseline solves it; the scenario is `tier: discriminating`.
