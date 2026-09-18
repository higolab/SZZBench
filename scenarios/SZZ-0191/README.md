# SZZ-0191: The other bug-introducing commit is in the method the fixed line calls

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

`c1` is harmless while the only caller, `knownFromMenu`, passes values that are
already normalized. `c3` adds a caller that passes raw user input, and only
then is a tag such as `" Release "` rejected.

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
