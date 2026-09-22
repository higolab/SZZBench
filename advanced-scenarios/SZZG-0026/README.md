# SZZG-0026: Copy followed by bug introduction only in the copied code

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `copy-propagation`, `clone-divergence`, `direct-bic-in-copy` |
| oracle | `exact_set`; required `c2` · BFC `c3` |
| graph features | operation `copy_file` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method avoids reporting a copying commit that carried no fault.

## Expected history

```text
c0: create original formatter
c1: copy formatter to report formatter
c2: introduce copied-code null handling bug
c3: fix copied formatter null handling
```
