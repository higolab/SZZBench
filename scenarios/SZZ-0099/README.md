# SZZ-0099: Synchronized modifier after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `synchronized-after-bic`, `plain-blame-control` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario is an honest **control** for modifier noise: between the BIC and
the BFC a commit adds the `synchronized` modifier to the methods of the class and
changes nothing else. One of the modified signature lines sits directly above the
faulty statement, so it is a plausible blame distraction, but the faulty line
itself is untouched.

## Commit structure

- `c0`: Adds `RateLimiter` with `hasCapacity()` (`used < limit`), `acquire()` and
  `used()`.
- `c1`: Changes the check to `used <= limit`, so a limit of *n* admits *n + 1*
  requests. This is the BIC.
- `c2`: Turns `public boolean hasCapacity()` into
  `public synchronized boolean hasCapacity()` and `public void acquire()` into
  `public synchronized void acquire()`. Only the two modifiers are added: no
  rename, no parameter change, no body edit.
- `c3`: Restores `return used < limit;`. This is the BFC. Its first-parent diff is
  `+1 -1` on a single line; both `synchronized` modifiers stay.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`return used <= limit;`). `git blame` at
`c3^` on that line returns **`c1`**: **exact**. The generator's verification
reports `I700` (basic blame reaches the expected BIC).

## What a tool must do

To pass, a tool only has to blame the deleted line. It must not widen the
candidate set to `c2`, neither because `c2` is the most recent change to the file
nor because `c2` changed the signature line of the very method that is fixed.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`; all
  identifiers (`used`, `limit`) are declared as fields in `c0`.
- Behaviour probe over nine limits (`Integer.MIN_VALUE`, `-3`, `-1`, `0`, `1`,
  `2`, `3`, `5`, `10`), each with 13 successive `acquire()` calls and a
  `hasCapacity()` reading before every call, plus a limiter constructed with
  `Integer.MAX_VALUE` and two "how many requests are granted" loops for the
  limits 1 and 5 — 121 outputs in total. The `c1` snapshot differs from `c0`
  exactly when `used == limit` (and grants 2 instead of 1, and 6 instead of 5,
  requests in the two loops); the `c3` snapshot agrees with `c0` on every probed
  input.
