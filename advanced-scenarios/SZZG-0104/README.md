# SZZG-0104: Configuration BIC is fixed by code-side normalization

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `configuration-change`, `cross-artifact-fix`, `context-dependent` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

The fault is a trailing slash added to `api.host` in a properties file; the fix
normalises the value in Java. The bug-fixing commit opens no file the fault
touched, so a tool has to cross from code to configuration.

Until 2026-09-21 nothing in the repository read `api.host`, so the declared BIC
could not cause the fault the BFC fixed (issue #23). `AppConfig` now loads
`app.properties` from the classpath and `ApiClient` passes `api.host` to
`Endpoint.url`, and the effect is measured below.

## Commit structure (generated)

```text
* b2165d4  Strip trailing slashes when building the endpoint URL
* aa54a14  Add a trailing slash to the API host
* 32e993b  Add the endpoint resolver, the API client and their configuration
```

- `c0`: `Endpoint.url(host)` returns `host + "/api"`; `AppConfig` reads `api.host = https://example.com`; `ApiClient.apiUrl()` joins them.
- `c1` (BIC): `app.properties` only — `api.host=https://example.com/`.
- `c2` (BFC): `Endpoint.java` only — strips trailing slashes before appending `/api`.

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c2`

## Measured behaviour and blame

`ApiClient.apiUrl()`: `https://example.com/api` at `c0`,
**`https://example.com//api`** at `c1`, `https://example.com/api` at `c2`
(`tests/test_twins_and_transitions.py`, with `src/main/resources` on the
classpath). Blaming the line `c2` deletes in `Endpoint.java` returns `c0`;
nothing the fix touches was written by `c1`.

## What a tool must do

Report `c1`, a commit that changed only a properties file, from a fix that
changed only Java. Blame on the fix points at `c0`.
