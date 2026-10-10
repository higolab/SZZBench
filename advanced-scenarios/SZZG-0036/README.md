# SZZG-0036: Fix split across multiple commits

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `multi-bfc`, `test-file-added` |
| oracle | `exact_set`; required `c1` · BFCs `c3`, `c4` |
| graph features | 2 BFCs; `fix_series` |
<!-- /szzbench:header -->

## Purpose

SZZG-0029 with one more commit. The fault (`c1` makes both bounds of `Range.contains` exclusive) and
the two fixes (`c3` accepts the lower bound again, `c4` the upper) are SZZG-0029's. `c2`, between the
fault and the first fix, adds `src/test/java/example/RangeTest.java`, a test file holding only its
package line and a comment that states the expected behaviour. The scenario's `fix_series` lists
`c2`, `c3` and `c4` as one series, as a developer who writes the test first would see the work, but
only `c3` and `c4` are bug-fixing commits.

The scenario is a control: the test-only commit must change nothing. `c2` deletes no line, so a
method that takes the whole series as the fix has nothing more to blame; it touches no line of
`Range.java`, so a method that starts from `c3` and `c4` never meets it. Each fix leads to `c1`
(scored per fix, `docs/evaluation-policies.md` §1.7), exactly as in SZZG-0029. A method that reports
`c2`, or answers here differently from SZZG-0029, is reacting to a commit that touches only test
code. The position, shape and blame baselines of `szzbench baselines` score the two scenarios alike.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/Range.java)
c1: introduce bug (replace src/main/java/example/Range.java)
c2: add test context (write_file src/test/java/example/RangeTest.java)
c3: fix bug (replace src/main/java/example/Range.java)
c4: fix bug (replace src/main/java/example/Range.java)
```
