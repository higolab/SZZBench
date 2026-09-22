# SZZG-0126: The fix is a git revert of the faulty commit, after another revert that is not

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `revert`, `revert-is-fix`, `resolvable-message-handle`, `revert-as-distractor` |
| oracle | `exact_set`; required `c1`; related but not correct `c2`, `c3` · BFC `c4` |
| defeats | `shape` |
| graph features | revert `c3`, `c4` |
<!-- /szzbench:header -->

## Purpose

The other revert scenarios use a revert to bring a bug back. Here the revert is
the fix: `c4` is a real `git revert` of the faulty commit `c1`, so its subject
quotes `c1`'s subject and its body names `c1`'s hash — a handle a
message-aware tool can resolve directly. One commit earlier, `c3` is an equally
real `git revert` of an unrelated commit, so the history holds two reverts and
only one of them is the fix.

## Commit structure (generated)

```text
* 5427464  Revert "Treat an entry as stale once its age reaches the ttl"   <- BFC (c4) = git revert c1
* dad2e9e  Revert "Add a describe method for the cache dashboard"          (c3) = git revert c2
* 453cad8  Add a describe method for the cache dashboard                   (c2)
* b428897  Treat an entry as stale once its age reaches the ttl            <- BIC (c1)
* 37603f2  Add the cache freshness check                                   (c0)
```

Both reverts are produced by `git revert --no-commit`; their bodies are git's:

```text
5427464  This reverts commit b42889783917057f608f976f4bc4c02c03350832.   (= c1)
dad2e9e  This reverts commit 453cad8dfaf7647a0bb39e4b48ef1700487e6ca6.   (= c2)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- `related_but_not_correct`: `c2` (the method the other revert removed), `c3` (that revert)
- BFC: `c4`

## Measured blame outcome at BFC^

Blaming the line `c4` deletes returns `c1`; the verifier reports `GI703`.

## What a tool must do

Report `c1`. Reading footers alone, a tool sees two `This reverts commit`
lines; it has to notice that `c4` restores the freshness comparison while `c3`
restores a removed method. "The most recent revert's target" happens to be
right here; "every reverted commit" is not.
