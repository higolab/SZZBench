# SZZG-0057: test failure から原因推定可能

## Source

- Source scenario: `FUTURE-057`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

テストの失敗内容を見れば BIC が推定できるが、コード差分だけでは難しいケースを評価する。

## Expected history

```text
c1: bug introduced
c2: failing test added
c3: fix
```

## Why this needs `scenario.graph.yml`

test failure や expected/actual output を表現できない。

## Required graph-schema features

```yaml
test_context:
  failing_tests:
    - name: "RangeTest.boundaryValues"
      introduced_in: "c2"
      failure_message: "expected true but was false"
```

## Evaluation points

- test-aware SZZ
- LLM による failure explanation 利用
- test追加commitの扱い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0057/
├── scenario.graph.yml
└── README.md
```
