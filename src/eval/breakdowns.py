"""Headline metrics, per-turn-index curves, and report-grade breakdowns.

Every rate in the output is a `{correct, n, accuracy}` triple so the report
can quote sample sizes alongside percentages — small buckets need that
context to be defensible.

Headline metrics (each defended in the report):
  - per-turn execution accuracy: standard ConvFinQA metric.
  - per-conversation accuracy: every turn correct in a record. Catches
    cascade failures the per-turn number hides.
  - conditional accuracy P(turn_i correct | turn_{i-1} correct), per i.
    Disambiguates cascade failure from intrinsic late-turn difficulty: a
    flat curve points to cascade; a falling curve points to degradation.

Tomoro-grade breakdowns:
  - by question type (Type I / Type II) — paper sec 5.3/6.3 calls Type II
    the harder subset; we report it explicitly.
  - by gold format (numeric / boolean) — different reasoning paths in the
    model; ~44/14k turns are boolean and would otherwise hide in the mean.
  - by doc feature (`has_duplicate_columns`, `has_non_numeric_values`) —
    validates the "do nothing" cleaning policy from the data plan.

Cost block: token totals, USD estimate, total seconds, plus mean latency
and mean input-tokens by turn index — the latter is the evidence that
input-context grows with turn (motivating prompt caching as a future
optimization).
"""

from collections import defaultdict
from typing import Any, Iterable


def summarize(
    rows: Iterable[Any],
    *,
    price_per_mtok_input: float = 0.0,
    price_per_mtok_output: float = 0.0,
) -> dict[str, Any]:
    rows = list(rows)
    if not rows:
        return _empty_summary()

    by_record: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_record[r.record_id].append(r)
    for record_rows in by_record.values():
        record_rows.sort(key=lambda r: r.turn_idx)

    n_turns_correct = sum(1 for r in rows if r.correct)
    n_records_all_correct = sum(
        1 for record_rows in by_record.values() if all(r.correct for r in record_rows)
    )

    return {
        "n_turns": len(rows),
        "n_records": len(by_record),
        "n_turns_correct": n_turns_correct,
        "n_records_all_correct": n_records_all_correct,
        "per_turn_accuracy": _rate(n_turns_correct, len(rows)),
        "per_conversation_accuracy": _rate(n_records_all_correct, len(by_record)),
        "per_turn_idx_accuracy": _per_turn_idx_accuracy(rows),
        "conditional_accuracy": _conditional_accuracy(by_record),
        "accuracy_by_question_type": _accuracy_by_bool(
            rows,
            lambda r: r.has_type2_question,
            true_label="type_ii",
            false_label="type_i",
        ),
        "accuracy_by_gold_format": _accuracy_by_gold_format(rows),
        "accuracy_by_doc_feature": {
            "has_duplicate_columns": _accuracy_by_bool(
                rows, lambda r: r.has_duplicate_columns
            ),
            "has_non_numeric_values": _accuracy_by_bool(
                rows, lambda r: r.has_non_numeric_values
            ),
        },
        "cost": _cost_block(rows, price_per_mtok_input, price_per_mtok_output),
    }


def _rate(correct: int, n: int) -> dict[str, Any]:
    return {
        "correct": correct,
        "n": n,
        "accuracy": (correct / n) if n else None,
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "n_turns": 0,
        "n_records": 0,
        "n_turns_correct": 0,
        "n_records_all_correct": 0,
        "per_turn_accuracy": _rate(0, 0),
        "per_conversation_accuracy": _rate(0, 0),
        "per_turn_idx_accuracy": {},
        "conditional_accuracy": {},
        "accuracy_by_question_type": {"type_i": _rate(0, 0), "type_ii": _rate(0, 0)},
        "accuracy_by_gold_format": {"numeric": _rate(0, 0), "boolean": _rate(0, 0)},
        "accuracy_by_doc_feature": {
            "has_duplicate_columns": {"true": _rate(0, 0), "false": _rate(0, 0)},
            "has_non_numeric_values": {"true": _rate(0, 0), "false": _rate(0, 0)},
        },
        "cost": {
            "tokens_in_total": 0,
            "tokens_out_total": 0,
            "usd_estimate": 0.0,
            "total_seconds": 0.0,
            "mean_latency_ms_by_turn_idx": {},
            "mean_tokens_in_by_turn_idx": {},
        },
    }


def _per_turn_idx_accuracy(rows: list[Any]) -> dict[str, dict[str, Any]]:
    buckets: dict[int, list[bool]] = defaultdict(list)
    for r in rows:
        buckets[r.turn_idx].append(r.correct)
    return {str(idx): _rate(sum(c), len(c)) for idx, c in sorted(buckets.items())}


def _conditional_accuracy(by_record: dict[str, list[Any]]) -> dict[str, dict[str, Any]]:
    """For each i ≥ 1, accuracy on records whose turn (i-1) was correct.

    Indices appear in the output for any i where some record has turn i —
    so a missing key never happens silently. `n=0` (no record had prior
    correct) is reported with `accuracy=None`.
    """
    cond_buckets: dict[int, list[bool]] = defaultdict(list)
    cond_indices: set[int] = set()
    for record_rows in by_record.values():
        for i in range(1, len(record_rows)):
            cond_indices.add(i)
            if record_rows[i - 1].correct:
                cond_buckets[i].append(record_rows[i].correct)
    return {
        str(idx): _rate(sum(cond_buckets[idx]), len(cond_buckets[idx]))
        for idx in sorted(cond_indices)
    }


def _accuracy_by_bool(
    rows: list[Any],
    predicate,
    *,
    true_label: str = "true",
    false_label: str = "false",
) -> dict[str, dict[str, Any]]:
    true_correct = true_n = false_correct = false_n = 0
    for r in rows:
        if predicate(r):
            true_n += 1
            true_correct += int(r.correct)
        else:
            false_n += 1
            false_correct += int(r.correct)
    return {
        true_label: _rate(true_correct, true_n),
        false_label: _rate(false_correct, false_n),
    }


def _accuracy_by_gold_format(rows: list[Any]) -> dict[str, dict[str, Any]]:
    """Boolean = gold is a string ('yes'/'no'); numeric = gold is a float."""
    return _accuracy_by_bool(
        rows,
        lambda r: isinstance(r.gold, str),
        true_label="boolean",
        false_label="numeric",
    )


def _cost_block(rows: list[Any], price_in: float, price_out: float) -> dict[str, Any]:
    tokens_in_total = sum(r.tokens_in for r in rows)
    tokens_out_total = sum(r.tokens_out for r in rows)
    usd_estimate = (
        tokens_in_total * price_in / 1_000_000
        + tokens_out_total * price_out / 1_000_000
    )
    total_seconds = sum(r.latency_ms for r in rows) / 1000.0

    latency_buckets: dict[int, list[int]] = defaultdict(list)
    tokens_in_buckets: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        latency_buckets[r.turn_idx].append(r.latency_ms)
        tokens_in_buckets[r.turn_idx].append(r.tokens_in)

    return {
        "tokens_in_total": tokens_in_total,
        "tokens_out_total": tokens_out_total,
        "usd_estimate": usd_estimate,
        "total_seconds": total_seconds,
        "mean_latency_ms_by_turn_idx": {
            str(idx): sum(v) / len(v) for idx, v in sorted(latency_buckets.items())
        },
        "mean_tokens_in_by_turn_idx": {
            str(idx): sum(v) / len(v) for idx, v in sorted(tokens_in_buckets.items())
        },
    }
