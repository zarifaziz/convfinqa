"""Evaluation primitives: answer comparison, metric aggregation."""

from src.eval.breakdowns import summarize
from src.eval.metrics import compare_answer

__all__ = ["compare_answer", "summarize"]
