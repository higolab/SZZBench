# SZZG-0065: chmod only

## Source

- Source scenario: `FUTURE-065`
- Category: robustness / 実装品質確認系未対応シナリオ

## Purpose

file mode 変更のみの commit が含まれる場合に SZZ が誤動作しないか確認する。

## Expected history

```text
c0: script を追加
c1: chmod +x のみ
c2: code bug
c3: fix
```

## Why this needs `scenario.graph.yml`

file mode change を表現できない。

## Required graph-schema features

```yaml
- type: "chmod"
  path: "scripts/run.sh"
  mode: "755"
```

## Evaluation points

- file mode only commit の扱い
- diff parser の robustness
- false positive の有無

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0065/
├── scenario.graph.yml
└── README.md
```
