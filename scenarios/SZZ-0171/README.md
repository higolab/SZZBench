# SZZ-0171: Dependency update as BIC

## Summary

The fault is introduced by a dependency upgrade rather than by a source edit. `c0` adds
`RangeAdapter`, which calls `RangeLib.includes`, and declares `org.example:range-lib` in
`pom.xml`. `c1` -- the BIC -- touches only `pom.xml`, upgrading `range-lib` to `2.0.0`,
in which the range semantics changed. `c2` fixes the fault in source, by calling
`RangeLib.containsInclusive` instead.

Measured: `git blame` of the line the fix replaces (`return RangeLib.includes(...)`) at
`c2^` returns **`c0`**, not `c1`. The source line the fix rewrites was written by `c0`
and never touched since, so a line-level SZZ that follows the fix's deleted line cannot
reach the BIC at all; `c1` appears only in `pom.xml`.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- This is the only scenario in the suite that ships a build file, and it does **not** compile
  with `javac` alone: `org.example:range-lib` is declared in `pom.xml`, is not vendored, and is
  fictional, so it resolves nowhere. That is intended -- see `docs/decisions/vocabulary.md` §4
  on what "every Java snapshot compiles" means. Vendoring `RangeLib` into the repository would
  turn the dependency upgrade into an ordinary in-repo source edit, which is a different scenario.
- Moved from SZZG-0004 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
