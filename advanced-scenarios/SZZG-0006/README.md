# SZZG-0006: Extract class after BIC

## Purpose

`OrderService` parses quantities and reports orders. `c1` makes `parseQuantity`
swallow `NumberFormatException` and return 0, so a malformed quantity is
silently accepted as none. `c2` extracts a `QuantityParser` class and moves the
buggy method there; `c3` fixes it in the extracted class by throwing. The BIC
and the BFC are in different files, and the file the fix touches did not exist
at the BIC. Compare SZZG-0005, where a method is moved without splitting
responsibilities.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, two distractors on
the fault file, 4 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* 082de7e  2024-02-08  Reject a malformed quantity in the extracted parser     <- BFC (c3; QuantityParser.java)
* c82ff34  2024-02-05  Extract QuantityParser from OrderService                (c2, extract class)
* 2ed3933  2024-01-25  Never fail on a malformed quantity                      <- BIC (c1; OrderService.java)
* 5610a25  2024-01-18  Add OrderService with quantity parsing and reporting    (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c3`

## Measured behaviour and blame

| commit | `describeParsed("SKU-1", " 4 ")` | `describeParsed("SKU-1", "x")` |
|---|---|---|
| `c0` | `SKU-1 x 4` | throws `NumberFormatException` |
| `c1`, `c2` | `SKU-1 x 4` | **`SKU-1 x 0`** |
| `c3` | `SKU-1 x 4` | throws `IllegalArgumentException("not a quantity: x")` |

`c3` deletes one line (`return 0;`, line 8 of `QuantityParser.java`); blame at
`c3^` returns `c2`, the extraction. The declared fault statement is no longer in
`OrderService.java` at `c3^` (verifier `GI701`, declared by the refactoring
factors).

## What a tool must do

Report `c1`. The extracted method's body is identical to the one `c1` wrote in
`OrderService.java`; a tool has to follow the code across the extraction rather
than stop at the commit that created the new file.

## Factors

- `refactoring`
- `extract-class`
- `method-move`
- `post-bic-refactoring`
- `exception-swallowed`
