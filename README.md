# szzbench generator implementation

This package provides a minimal implementation of the SZZ synthetic benchmark generator.

Supported initial scope:

- Linear Git history only.
- `write_file` and `replace` operations.
- `scenario.yml` as the source of truth.
- `validate`, `validate --simulate`, `generate`, `verify`, and `clean` commands.
- Deterministic Git commits using author/date from the scenario.
- `commit-map.json`, `validation-result.json`, `verify-result.json`, and `generation.log`.

## Install

```bash
pip install -e ".[dev]"
```

## Validate

```bash
szzbench validate examples/basic/simple-line-modification/scenario.yml
szzbench validate --simulate examples/basic/simple-line-modification/scenario.yml
```

## Generate

```bash
szzbench generate \
  examples/basic/simple-line-modification/scenario.yml \
  --out generated-input-repos/basic/simple-line-modification/default \
  --force
```

Generated layout:

```text
generated-input-repos/basic/simple-line-modification/default/
  repo/
  metadata/
    scenario.yml
    commit-map.json
    validation-result.json
    verify-result.json
    generation.log
```

## Verify

```bash
szzbench verify \
  generated-input-repos/basic/simple-line-modification/default/repo \
  --scenario examples/basic/simple-line-modification/scenario.yml
```

## Clean

```bash
szzbench clean
szzbench clean --dry-run
szzbench clean --root generated-input-repos
```

`clean` removes generated outputs under `generated-input-repos` by default. A generated output is a directory containing the generator layout, including `repo/.git` and `metadata/`.

## Notes

The generator intentionally fails on ambiguous or unsupported inputs. It does not modify scenario or oracle fields.
