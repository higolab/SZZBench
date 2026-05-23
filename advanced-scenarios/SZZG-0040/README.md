# SZZG-0040: release branch only bug

## Source

- Source scenario: `FUTURE-040`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

main には存在しない release branch 固有の bug を評価する。

## Expected history

```text
main:    c0 -- c1正常
release: c0 -- r1 release-specific bug -- r2 fix
```

## Why this needs `scenario.graph.yml`

branch-specific file state と oracle が必要。

## Required graph-schema features

```yaml
bugs:
  - id: "B001"
    branches:
      affected:
        - "release"
      unaffected:
        - "main"
```

## Evaluation points

- branch-specific BIC/BFC
- main だけを見た SZZ が誤るか
- release maintenance dataset の再現

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0040/
├── scenario.graph.yml
└── README.md
```
