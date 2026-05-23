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

## Download-only fallback

The editor also supports downloading:

- `scenario.yml`
- `README.md`
- `index-entry.yml`

These can be manually placed into `scenarios/SZZ-XXXX/`.

## Scope of this first version

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

Not supported yet:

- running Python validator/generator from the web UI,
- multiple files,
- multiple bugs,
- branch/merge histories,
- loading and editing existing scenarios.
