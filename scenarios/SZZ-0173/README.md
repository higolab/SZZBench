# SZZ-0173: File creation only as fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `file-creation-fix` |
| oracle | `exact_set`; required `c0` · BFC `c1` |
<!-- /szzbench:header -->

## Summary

The BFC consists solely of adding a new file. `PluginLoader.loadDefault()` resolves `example.DefaultPlugin`
reflectively by class name, so the code compiles without `DefaultPlugin.java` but fails at runtime with
`ClassNotFoundException` until the class is added. This is an addition-only ("ghost") fix by design: the BFC
modifies or deletes no existing line, so there is nothing in the BFC diff for a plain blame-based SZZ to trace.

## Commit structure

- `c0` (BIC): adds `PluginLoader` with

  ```java
  public Object loadDefault() throws ReflectiveOperationException {
      return Class.forName("example.DefaultPlugin").getDeclaredConstructor().newInstance();
  }
  ```

  `DefaultPlugin.java` does not exist, so `loadDefault()` throws `ClassNotFoundException: example.DefaultPlugin`.
- `c1` (BFC): adds `src/main/java/example/DefaultPlugin.java`; `loadDefault()` now returns a `DefaultPlugin`.

Both snapshots compile with `javac`. Running `new PluginLoader().loadDefault()` against the generated
repository throws `ClassNotFoundException` at `c0` and returns an `example.DefaultPlugin` instance at `c1`.

## Expected SZZ behaviour

- Bug-introducing commit(s): `c0`
- Bug-fixing commit: `c1`
- Fault type: omission (`DefaultPlugin` is missing while `PluginLoader.java` references it)
- Fix type: file creation (`public class DefaultPlugin`)

## Expected plain-blame behaviour

The BFC diff is `DefaultPlugin.java | 7 +++++++` (additions only). Consequently:

| What is blamed at `c1^` | Result |
|---|---|
| Any line of `DefaultPlugin.java` | not possible: the file does not exist at `c1^` |
| `Class.forName("example.DefaultPlugin")` in `PluginLoader.java` | `c0` |

A classic SZZ that blames only the lines deleted or modified by the BFC finds no candidate. Reaching `c0`
requires other evidence, for example blaming the line that references the newly created class, or treating
the commit that introduced the dangling reference as the origin of the omission.

## Notes

- Moved from SZZG-0065 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
- 2026-09 (issue 1): `PluginLoader.loadDefault()` previously returned `null` and nothing referenced
  `DefaultPlugin`, so the file creation did not fix anything observable. The loader now loads the class
  reflectively, which makes the missing file an actual runtime failure that `c1` repairs. The oracle is unchanged.
