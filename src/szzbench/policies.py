"""Shared evaluation-policy vocabulary.

The validator and the evaluator must agree on which `evaluation_policy`
names exist.  The evaluator keeps its own copy in
``szzbench.evaluator._SUPPORTED_GRAPH_POLICIES``; a test asserts that the two
sets are identical so that drift is caught without the validator importing
the evaluator.
"""
from __future__ import annotations

SUPPORTED_EVALUATION_POLICIES: frozenset[str] = frozenset(
    {
        "exact_set",
        "direct_only",
        "reintroduction_direct",
        "partial_credit",
        "top_k",
        "relaxed_with_related",
        "relaxed_with_credit",
    }
)
