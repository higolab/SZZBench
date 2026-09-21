# SZZ-0180: BIC is a large initial import

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `initial-import-bic`, `large-bic` |
| oracle | `exact_set`; required `c0` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks how SZZ implementations treat a bug whose inducing
commit is a large initial import. Several SZZ variants filter candidate
commits by size, by number of touched files, or discard the root commit
altogether (MA-SZZ- and RA-SZZ-style filters, "big-bang commit" heuristics).
Here the only correct answer is exactly such a commit.

## Commit structure

- `c0`: Imports the inventory module: nine Java files under
  `com.example.inventory` (`Sku`, `StockLevel`, `MovementType`,
  `StockMovement`, `Warehouse`, `ReorderPolicy`, `InventoryException`,
  `InventoryService`, `LowStockReport`), 232 lines in total.
  `InventoryService.reserve(...)` compares the requested quantity against
  on-hand stock instead of available stock, so already reserved units can be
  reserved again. This is the BIC.
- `c1`: Adds `Sku.toString()`.
- `c2`: Extends a report line in `LowStockReport`.
- `c3`: Changes `level.getOnHand()` to `level.available()` in
  `InventoryService.reserve(...)`. This is the BFC (`+1 -1`).

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c0`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line. `git blame` at `c3^` on that line
returns **`c0`**: exact. The difficulty of this scenario lies entirely in
candidate filtering, not in line tracing.

## What a tool must do

To pass, a tool must keep `c0` as a candidate even though it is the root
commit, touches nine files and adds 232 lines. Any filter that removes
large commits, multi-file commits or the initial commit produces an empty
answer here.
