# SZZBench Scenario Editor

This is a local web app for creating `scenario.yml` files for SZZBench.

The editor is designed for the first practical workflow:

- users input scenario metadata,
- users add multiple source-code versions,
- each version becomes one logical commit (`c0`, `c1`, `c2`, ...),
- `c0` is emitted as `write_file`,
- later versions are emitted as `replace` from the previous full source to the current full source,
- one bug oracle is emitted,
- the generated files can be downloaded or saved directly under `SZZBench/scenarios/`.

## Start

From this directory:

```bash
npm install
npm run dev
```

Then open:

```text
http://127.0.0.1:5173
```

## Save directly to `scenarios/`

Use the **Save to scenarios/** button. The local Node.js backend writes:

```text
SZZBench/scenarios/SZZ-XXXX/scenario.yml
SZZBench/scenarios/SZZ-XXXX/README.md
SZZBench/scenarios/index.yml
```

If the scenario ID already exists, the save is rejected unless **Overwrite existing scenario** is checked.

Saving goes through SZZBench's own checks before anything reaches `scenarios/` (issue #97):

1. `meta.tier` must be chosen (`control` or `discriminating`). It has no default, because it declares what the
   scenario is for (`docs/decisions/vocabulary.md` §7); the button stays disabled until it is set.
2. The files are written to a scratch copy of the layout, `szzbench readme --write` inserts the generated README
   header there, and `szzbench validate --lint` checks the result. Any error rejects the save and nothing is
   written; warnings and infos are saved and listed in the page.
3. `scenarios/index.yml` gets the one entry, inserted in id order (or replaced on overwrite); every other line
   of the file stays as it was.

The backend runs `python3 -m szzbench.cli` with this checkout's `src/` on `PYTHONPATH`, so the Python it finds
needs PyYAML (the SZZBench virtual environment does). Two environment variables change what it uses:

| variable | default | meaning |
|---|---|---|
| `SZZBENCH_PYTHON` | `python3` | the Python that runs the validator and the README renderer |
| `SZZBENCH_REPO_ROOT` | two directories above this one | the checkout whose `scenarios/` is written |

## Downloading instead of saving

The three **Download** buttons fetch what **Save to scenarios/** would write, after the same checks, and write
nothing into the repository:

- `scenario.yml`;
- `README.md`, with the generated header already inserted;
- `index-entry.yml`, the entry in `scenarios/index.yml`'s own style.

A scenario the save would refuse (no tier, a `validate --lint` error) is not downloaded either; the page shows why.
Files placed by hand in `scenarios/SZZ-XXXX/` then pass `szzbench validate --lint --strict` as saved ones do.

Without the backend only `scenario.yml` can be downloaded, because the header comes from SZZBench itself. Write the
README by hand and run `szzbench readme --write scenarios/SZZ-XXXX` before the scenario counts as ready: until then
`validate --lint` reports W455 ("README has no generated header").

## Conventions the generated files follow

- Commit messages describe the change and never its role (`docs/decisions/oracle-leakage.md`); a new version
  starts with an empty message, and the checks ask for one.
- One author writes every commit by default, so no author's commits coincide with the answer.
- Dates are optional; left empty, generation fills deterministic ones (`docs/generator-options.md` §1).
- The category is one of the codes S1-S8 with its name (`docs/decisions/vocabulary.md` §3); difficulty is
  `easy`, `medium` or `hard`.
- The README carries the hand-written sections only; the header is inserted on save.

`src/scenarioModel.ts` holds the state and everything the editor generates, with no React in it, so
`tests/test_scenario_editor.py` runs it with Node and checks the output with the Python validator; the same
file drives the save endpoint against a scratch copy of the repository.

## Scope

Supported:

- one scenario at a time,
- one source file,
- linear history,
- one bug oracle,
- one BIC,
- one BFC,
- `line_modification` and `omission`,
- YAML generation,
- direct save to `scenarios/` through a local Node.js backend.

Not supported:

- generating or verifying the repository from the web UI (run `szzbench generate` on the saved file),
- multiple files,
- multiple bugs,
- branch/merge histories,
- loading and editing existing scenarios.
