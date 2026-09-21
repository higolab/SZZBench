# Fault library for scenario authoring (issue #13)

**Status:** catalogue, decided 2026-09-21. It records the fault kinds the suite
already uses, with one exemplar each, so that a rewrite of a template-carrying
scenario picks a kind rather than inventing a spelling, and so that a category's
fault mix can be read off `szzbench coverage`'s *fault statement reuse* block.

## 1. Why

`szzbench coverage` (2026-09-21, 251 scenarios, before any rewrite) reported
that one statement, `return value > min && value < max;`, was a declared fault
statement of **83 scenarios** — 18 of 116 classic, **65 of 135 graph** (counting
`fault`, `faults[]` and `origin_faults[]`) — and the most reused statement in
every graph category but G6 (G4 17/28, G5 13/18, G2 10/16, G1 7/14, G8 5/10,
G3 5/14, G7 4/16, G9 2/10; G6's most reused is its sibling `boolean belowMax =
value < max;`, 5/9). Of the 159 distinct statements in the suite, 11 were shared
by two or more scenarios and the next most common, `boolean belowMax = value <
max;` and `return value > min;`, reach 6 each. The decided target (2026-09-21)
is **at most one third of every graph category** on its most reused statement,
which the twins keep; the G4 rewrites (SZZG-0045/0047/0049/0050/0051/0053/0054/
0056) brought G4 to **9/28** with 21 distinct statements, and the G5 rewrites
(SZZG-0069/0070/0073/0076/0081/0082/0083) brought G5 to **6/18** with 19
distinct statements; the suite stands at 68 carriers (50 graph) and 175
distinct statements. G2, G1, G8, G6 and G3 follow. Holding the fault constant while varying the history
is a legitimate controlled-experiment device, and the twins that depend on it
(SZZG-0043/0128, SZZG-0057/0122) keep it. But a tool that has seen the benchmark
can match the text, and the graph suite's fault-kind coverage is thin: most
blame-trivial graph scenarios differ only in history shape. The goal is
**balance, not elimination**; the measure of balance is the per-category share
of the most reused statement, printed by `szzbench coverage`.

## 2. The kinds

Names are the canonical fault factors of `vocabulary.md` §1.3. "Exemplar" is
correct → faulty. "In the suite" cites scenarios that carry the kind today
(their factors may still use an older spelling; the sweep of §1.4 maps them).

| kind | exemplar | observable failure | in the suite |
|---|---|---|---|
| `boundary-condition` | `value > limit` → `value >= limit` | the limit itself is treated as exceeded | SZZG-0140, SZZ-0083, SZZ-0204 (Python) |
| `off-by-one` | `Math.min(requested, max)` → `Math.min(requested, max - 1)`; `nights * 10000` → `(nights - 1) * 10000` | one element or one unit lost | SZZG-0130, SZZG-0139 |
| `wrong-operator` | `price + price / 10` → `price - price / 10`; `a \|\| b` → `a && b`; `//` → `/` (Python) | a surcharge becomes a discount; a guard never fires; a float index | SZZG-0139, SZZG-0124, SZZ-0201 |
| `boolean-negation` | `if (valid)` → `if (!valid)` | the branches swap | SZZ-0014 |
| `wrong-variable` | `% (shipped, total)` → `% (total, shipped)`; returning the wrong local | right shape, wrong value | SZZ-0205, SZZ-0015 |
| `wrong-constant` | `>= 80` → `>= 90`; `61440` → `6144`; `3000` → `30` | a threshold, ceiling or unit is off | SZZ-0021, SZZ-0206, SZZG-0142 |
| `null-check-omission` | `return s.trim();` without `if (s == null)`; `CARRIERS[code]` without `in` | `NullPointerException` / `KeyError` on the absent case | SZZ-0047, SZZ-0174, SZZ-0203 (Python) |
| `missing-break` | a `case` without `break` | fall-through into the next case | SZZ-0175 |
| `missing-branch` | a `switch` with no `case BULK` | the default value for a real kind | SZZ-0176, SZZG-0138 |
| `guard-removed` | `if (count == 0) return 0;` deleted | division by zero / empty-input misbehaviour | SZZ-0078, SZZ-0080, SZZ-0177 |
| `resource-not-closed` | a `BufferedWriter` never closed | data not flushed, handle leaked | SZZ-0189 |
| `api-misuse` | `String.format("%.2f", x)` without a `Locale`; `def f(tags=[])`; `Optional.get()` without a presence check | environment-dependent output; shared state; `NoSuchElementException` | SZZG-0135, SZZ-0202 (Python), SZZG-0101, SZZG-0103 |
| `config-value` | a unit or key changed in a `.properties` / `.gitattributes` file | code reads a raw or missing value | SZZ-0199, SZZG-0104, SZZG-0134 |
| `duplicate-statement` | the same faulty statement in two places, one fixed | the copy keeps failing | S6 scenarios (SZZ-0132, SZZ-0136, …) |
| `composite-fault` | an attempted fix that repairs one fault and introduces another | two observable effects in one commit | SZZG-0030 |
| `string-comparison` | `a.equals(b)` → `a == b` | equal strings compare unequal | *none yet* |
| `exception-swallowed` | `catch (IOException e) { }` | a failure is silently ignored | *none yet* |
| `integer-overflow` | `int total = a * b;` on large inputs | wrap-around | *none yet* |

Two kinds the suite uses have no canonical name yet and are filed under the
nearest one: **arithmetic truncation** (`cents * percent / 100` →
`cents / 100 * percent`, `(int) Math.round(x * 100)` → `(int) (x * 100)`;
SZZG-0138, SZZG-0141) under `wrong-operator`, and **environment dependence**
(SZZG-0135) under `api-misuse`. Adding `arithmetic-truncation` to §1.3 is
proposed with the first rewrite that needs it.

## 3. Rules for a rewrite (issue #13)

1. Keep the id, the history shape, the oracle and the category. A rewrite
   changes the *code*, not what the scenario tests; its `bic_depth`,
   `oracle_size` and `fault_file_distractors` in `szzbench coverage` must not
   change.
2. Leave a domain: no `Range`, no `value`/`min`/`max`. Choose a kind from §2
   that the category does not yet carry (or carries least), and declare it as a
   fault factor.
3. Measure before writing the README: compile every snapshot, run the code at
   every commit, blame the deleted lines at BFC^, and quote the results
   (`tests/test_twins_and_transitions.py` is where the behaviour check goes).
4. Twins stay twins: SZZG-0043/0128 and SZZG-0057/0122 are rewritten together
   or not at all, with pinned metadata, and their identity tests keep passing.
5. Re-run `szzbench coverage` and report the per-category share before and
   after in the PR.
