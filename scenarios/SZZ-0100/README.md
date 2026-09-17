# SZZ-0100: Try block rewrite after BIC

## Purpose

This scenario checks how SZZ implementations behave when an intermediate commit
wraps the faulty statement in a `try` block. The wrap re-indents the faulty line,
so the line's last change is the intermediate commit. The bug-fixing commit
repairs the statement *inside* the try block and leaves the `try`/`catch` in
place.

## Commit structure

- `c0`: Adds `TimeoutSetting` with `timeoutMillis(String)`
  (`Math.min(seconds * 1000, MAX_TIMEOUT_MS)`) and `defaultTimeoutMillis()`.
- `c1`: Rewrites the clamp as `Math.min(seconds, MAX_TIMEOUT_MS) * 1000`, which
  compares a value in seconds with a maximum in milliseconds, so the cap is
  effectively never applied. This is the BIC.
- `c2`: Wraps the method body in `try { … } catch (NumberFormatException e) { return DEFAULT_TIMEOUT_MS; }`.
  The faulty statement itself is unchanged apart from its indentation.
- `c3`: Restores `return Math.min(seconds * 1000, MAX_TIMEOUT_MS);` at the new
  indentation. This is the BFC. Its first-parent diff is `+1 -1` on a single
  line; the `try`/`catch` stays.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (the clamp inside the try block).
`git blame` at `c3^` on that line returns **`c2`**: plain blame **misses** the
BIC. Here `git blame -w` *does* reach `c1`, because `c2`'s change to this
particular line is whitespace-only — which is exactly what this scenario is meant
to separate from SZZ-0092 and SZZ-0096, where `-w` does not help.

## What a tool must do

To pass, a tool has to ignore the re-indentation: either by blaming with
whitespace-insensitive settings (`git blame -w`, which is enough here), or by
following the line history one step past `c2`.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`.
- Behaviour probe over 24 numeric settings (`"0"`, `"1"`, `"2"`, `"5"`, `"30"`,
  `"59"`, `"60"`, `"61"`, `"100"`, `"1000"`, `"59999"`, `"60000"`, `"60001"`,
  `"-1"`, `"-60"`, `"-2147483648"`, `"2147483647"`, `"2147483646"`, `"2147483"`,
  `"2147484"`, `" 30 "`, `"\t45\n"`, `"+7"`, `"000012"`), which include the
  values where `seconds * 1000` overflows, plus `defaultTimeoutMillis()` and a
  `null` setting. The `c1` snapshot differs from `c0` for every setting above 60
  seconds and for the overflow values (10 of the numeric outputs); the `c3`
  snapshot agrees with `c0` on **all** numeric settings and on `null` (both throw
  `NullPointerException`).
- Contract beyond that domain: for the seven non-numeric settings (`"abc"`,
  `""`, `"   "`, `"12abc"`, `"3.5"`, `"1 2"`, `"99999999999"`) `c0` throws
  `NumberFormatException` while `c2` and `c3` return the default of 3000 ms.
  That difference is introduced by `c2`, the commit that added the fallback, and
  is deliberately preserved by the fix.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `try-block-after-bic`
- `basic-blame-distractor`
