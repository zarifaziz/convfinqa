"""Snapshot tests for `summarize`; assert on the full output to catch shape drift."""

import pytest
from pydantic import BaseModel

from src.eval.breakdowns import summarize


class _Row(BaseModel):
    record_id: str
    turn_idx: int
    correct: bool
    gold: float | str = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    has_type2_question: bool = False
    has_duplicate_columns: bool = False
    has_non_numeric_values: bool = False


def _row(rid: str, idx: int, correct: bool, **overrides) -> _Row:
    return _Row(record_id=rid, turn_idx=idx, correct=correct, **overrides)


def _rate(correct: int, n: int) -> dict:
    return {"correct": correct, "n": n, "accuracy": (correct / n) if n else None}


def test_empty_rows_returns_zeroed_summary() -> None:
    summary = summarize([])
    assert summary["n_turns"] == 0
    assert summary["per_turn_accuracy"] == _rate(0, 0)
    assert summary["per_turn_idx_accuracy"] == {}
    assert summary["conditional_accuracy"] == {}
    assert summary["accuracy_by_question_type"] == {
        "type_i": _rate(0, 0),
        "type_ii": _rate(0, 0),
    }
    assert summary["cost"]["tokens_in_total"] == 0
    assert summary["cost"]["usd_estimate"] == 0.0


def test_two_records_full_breakdown() -> None:
    # rec_a: T T F (Type I, clean)
    # rec_b: T F F (Type II, has duplicate columns)
    rows = [
        _row("a", 0, True),
        _row("a", 1, True),
        _row("a", 2, False),
        _row("b", 0, True, has_type2_question=True, has_duplicate_columns=True),
        _row("b", 1, False, has_type2_question=True, has_duplicate_columns=True),
        _row("b", 2, False, has_type2_question=True, has_duplicate_columns=True),
    ]
    summary = summarize(rows)

    assert summary["n_turns"] == 6
    assert summary["n_records"] == 2
    assert summary["per_turn_accuracy"] == _rate(3, 6)
    assert summary["per_conversation_accuracy"] == _rate(0, 2)
    assert summary["per_turn_idx_accuracy"] == {
        "0": _rate(2, 2),
        "1": _rate(1, 2),
        "2": _rate(0, 2),
    }
    # turn 1 conditional: both records had t0 correct {T, F} -> 1/2.
    # turn 2 conditional: only rec_a had t1 correct {F} -> 0/1.
    assert summary["conditional_accuracy"] == {"1": _rate(1, 2), "2": _rate(0, 1)}
    # rec_a (Type I) -> 2/3 correct; rec_b (Type II) -> 1/3.
    assert summary["accuracy_by_question_type"] == {
        "type_i": _rate(2, 3),
        "type_ii": _rate(1, 3),
    }
    assert summary["accuracy_by_doc_feature"]["has_duplicate_columns"] == {
        "true": _rate(1, 3),
        "false": _rate(2, 3),
    }


def test_conditional_is_none_when_no_prior_correct() -> None:
    rows = [
        _row("a", 0, False),
        _row("a", 1, True),
        _row("b", 0, False),
        _row("b", 1, True),
    ]
    summary = summarize(rows)
    assert summary["conditional_accuracy"] == {"1": _rate(0, 0)}
    assert summary["conditional_accuracy"]["1"]["accuracy"] is None


def test_gold_format_splits_numeric_and_boolean() -> None:
    rows = [
        _row("a", 0, True, gold=42.0),
        _row("a", 1, False, gold=43.0),
        _row("a", 2, True, gold="yes"),
        _row("a", 3, False, gold="no"),
    ]
    summary = summarize(rows)
    assert summary["accuracy_by_gold_format"] == {
        "numeric": _rate(1, 2),
        "boolean": _rate(1, 2),
    }


def test_cost_block_aggregates_tokens_and_pricing() -> None:
    # 2 turns × 1000 input @ $3/MTok = $0.006; 2 turns × 100 output @ $15/MTok = $0.003.
    # Total = $0.009.
    rows = [
        _row("a", 0, True, tokens_in=1000, tokens_out=100, latency_ms=2000),
        _row("a", 1, True, tokens_in=1000, tokens_out=100, latency_ms=3000),
    ]
    summary = summarize(rows, price_per_mtok_input=3.0, price_per_mtok_output=15.0)
    cost = summary["cost"]
    assert cost["tokens_in_total"] == 2000
    assert cost["tokens_out_total"] == 200
    assert cost["usd_estimate"] == pytest.approx(0.009)
    assert cost["total_seconds"] == 5.0
    assert cost["mean_latency_ms_by_turn_idx"] == {"0": 2000.0, "1": 3000.0}
    assert cost["mean_tokens_in_by_turn_idx"] == {"0": 1000.0, "1": 1000.0}
