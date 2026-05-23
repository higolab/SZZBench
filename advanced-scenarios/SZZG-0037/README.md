# SZZG-0037: backport fix

## Source

- Source scenario: `FUTURE-037`
- Category: branch / merge / cherry-pick / backport 系未対応シナリオ

## Purpose

main で修正されたバグが release branch に backport されるケースを評価する。

## Expected history

```text
main:    c1 bug ---- c2 fix
release: r1 bug ---- r2 backport fix
```

## Why this needs `scenario.graph.yml`

branch 関係、backport relation、branch-specific BIC/BFC が必要。

## Required graph-schema features

```yaml
commits:
  - id: "r2"
    role: "backport_fix"
    backport_of: "c2"
```

## Evaluation points

- release branch での BIC はどれか
- main の BIC と release の BIC の対応
- backport commit をどう評価するか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0037/
├── scenario.graph.yml
└── README.md
```
