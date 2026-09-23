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
0056) brought G4 to **9/28** with 21 distinct statements, the G5 rewrites
(SZZG-0069/0070/0073/0076/0081/0082/0083) brought G5 to **6/18** with 19
distinct statements, the G2 rewrites (SZZG-0016/0017/0019/0021/0024) brought
G2 to **5/16** with 15 distinct statements, and the last batch
(SZZG-0005/0006/0007 in G1, SZZG-0107/0108 in G8, SZZG-0088/0091 in G6,
SZZG-0035 in G3) brought G1 to **4/14**, G8 to **3/10**, G6 to **3/9** and G3
to **4/14**. Every graph category is now at or below one third on its most
reused statement; the suite stands at 57 carriers (39 graph, 18 classic) and
186 distinct statements. The classic S3 group (11/37) keeps the template as its
controlled noise family and was not part of the decision. Holding the fault constant while varying the history
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
| `guard-removed` | `if (count == 0) return 0;` deleted; half of `if (user == null \|\| !user.isActive())` dropped | division by zero / empty-input misbehaviour; an authorization check that inactive accounts pass | SZZ-0078, SZZ-0080, SZZ-0177, SZZ-0211 |
| `resource-not-closed` | a `BufferedWriter` never closed | data not flushed, handle leaked | SZZ-0189 |
| `api-misuse` | `String.format("%.2f", x)` without a `Locale`; `def f(tags=[])`; `Optional.get()` without a presence check; `startsWith` where `contains` was meant | environment-dependent output; shared state; `NoSuchElementException`; a path-traversal check that only catches a leading `..` | SZZG-0135, SZZ-0202 (Python), SZZG-0101, SZZG-0103, SZZG-0073, SZZ-0171, SZZ-0209 |
| `config-value` | a unit, limit or key changed in a `.properties` / `.gitattributes` file | code reads a raw, narrowed or missing value | SZZ-0172, SZZ-0199, SZZ-0208, SZZG-0104, SZZG-0112, SZZG-0134 |
| `duplicate-statement` | the same faulty statement in two places, one fixed | the copy keeps failing | S6 scenarios (SZZ-0132, SZZ-0136, …) |
| `composite-fault` | an attempted fix that repairs one fault and introduces another | two observable effects in one commit | SZZG-0030 |
| `string-comparison` | `a.equals(b)` → `a == b`; comparing against a literal in the wrong case | equal strings compare unequal; a configured value stops matching | SZZG-0045, SZZ-0207 |
| `exception-swallowed` | `catch (IOException e) { }` | a failure is silently ignored | *none yet* |
| `integer-overflow` | `int total = a * b;` on large inputs; a dropped `(long)` cast | wrap-around; a size limit that a large declaration passes | SZZG-0056, SZZG-0076, SZZ-0210 |

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
6. **The reference arithmetic must be right across the domain the scenario
   admits** (decided 2026-09-23, issue #82). Four PR reviews in a row found the
   same defect: an expression presented as the *reference* or the *fix*
   overflows Java `int` for an input inside the declared range, so the
   scenario's premise is false there and the faulty expression is the accurate
   one. A README's behaviour table, a counterfactual and the claim that the BFC
   is a fix all rest on that premise. Either:
   - take the product in 64 bits — `(int) ((long) a * b / c)` — **in the faulty
     form as well as the correct one**, so the declared fault stays the only
     difference between them at every input; or
   - state the supported domain in the scenario's `notes` and probe its
     boundary.

   Either way the boundary is measured: `tests/test_reference_arithmetic.py`
   holds one row per audited scenario — the domain and the exact answer at the
   top of it, evaluated against the bug-fixing snapshot. Pick a boundary value
   that **also exposes the fault** where one exists, so the probe earns its
   place twice (SZZ-0218 uses `boxes(Integer.MAX_VALUE)`, SZZG-0148
   `netCents(999999999, 33)`).

   A bound has to clear **every** method that consumes the bounded quantity, not
   only the one whose expression was flagged: SZZG-0139's base price fits `int`
   for one night longer than the booking with its weekend surcharge does, so the
   scenario's bound is the surcharge's, 195 225 nights (PR #83 review).

   Where overflow *is* the declared fault — SZZ-0210, SZZG-0056, SZZG-0076, and
   SZZG-0141's `c2`, whose message gives avoiding it as the motive for the
   truncation it introduces — the arithmetic is correct as written. Repairing
   SZZG-0141 meant widening the **fix**, not the faulty form: `c2`'s motive was
   sound and its cure was not, which is the sharper lesson.

   Where a scenario **probes its own overflow on purpose**, widening is a
   regression, not a repair: SZZ-0100's README pins 24 settings that include the
   values where `seconds * 1000` wraps, and `c0` and `c3` share their answers,
   so a 64-bit conversion there both breaks pinned probes and lets a negative
   setting past the cap the scenario is about. Such a scenario writes its domain
   down and keeps its arithmetic.
