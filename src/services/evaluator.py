"""Evaluator service.

Owns the load -> answer -> score -> write loop. Depends on the
`DatasetRepository` Protocol (not the concrete JSON repo) and an `Answerer`,
so it's testable with a fake repo + fake LLM client.

Writes three sibling files in the run dir:
  - `transcripts.jsonl` / `transcripts.md` — one entry per LLM call, full
    audit trail for replay.
  - `predictions.jsonl` — one line per turn, lightweight grading record.
  - `summary.json` — overall metrics + breakdowns (no per-row detail; that
    lives in `predictions.jsonl`).
"""

import json
import random
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel

from src.domain import ConvFinQARecord
from src.eval.breakdowns import summarize
from src.eval.metrics import compare_answer
from src.repository.convfinqa import DatasetRepository
from src.services import anthropic
from src.services.answerer import Answerer, AnswerCall
from src.services.transcripts import write_transcript, write_transcript_md


class EvalRow(BaseModel):
    record_id: str
    turn_idx: int
    question: str
    predicted_answer: str
    predicted_unit: str
    predicted_calculation: str
    predicted_reasoning: str
    gold: float | str
    correct: bool
    latency_ms: int
    tokens_in: int
    tokens_out: int
    # Record-level features denormalized onto each row so breakdowns can
    # slice without re-loading the dataset.
    has_type2_question: bool
    has_duplicate_columns: bool
    has_non_numeric_values: bool


class EvalSummary(BaseModel):
    """Run output. `breakdown` is the full output of `summarize`; `rows` is
    the per-turn detail (excluded when serialised to summary.json — that
    detail lives in predictions.jsonl).
    """

    split: str
    seed: int | None = None
    rows: list[EvalRow]
    breakdown: dict[str, Any]


class Evaluator:
    def __init__(
        self,
        repo: DatasetRepository,
        answerer: Answerer,
        tol_abs: float,
        tol_rel: float,
        price_per_mtok_input: float = 0.0,
        price_per_mtok_output: float = 0.0,
    ) -> None:
        self._repo = repo
        self._answerer = answerer
        self._tol_abs = tol_abs
        self._tol_rel = tol_rel
        self._price_in = price_per_mtok_input
        self._price_out = price_per_mtok_output

    def run(
        self,
        split: str,
        run_dir: Path,
        n: int | None = None,
        record_id: str | None = None,
        seed: int | None = None,
    ) -> EvalSummary:
        # Always log the effective seed so a "random" run is reproducible later.
        effective_seed = seed if seed is not None else random.SystemRandom().randint(0, 2**31 - 1)
        logger.info(f"sample seed: {effective_seed}")

        records = self._select_records(
            split, n=n, record_id=record_id, seed=effective_seed
        )
        transcripts_path = run_dir / "transcripts.jsonl"
        transcripts_md_path = run_dir / "transcripts.md"
        predictions_path = run_dir / "predictions.jsonl"
        summary_path = run_dir / "summary.json"

        n_total_turns = sum(len(r.dialogue.conv_questions) for r in records)
        logger.info(
            f"evaluating {len(records)} record(s) "
            f"({n_total_turns} turns total) on split={split!r}"
        )

        rows: list[EvalRow] = []
        for idx, record in enumerate(records):
            record_rows = self._score_conversation(
                record, transcripts_path, transcripts_md_path
            )
            rows.extend(record_rows)
            with predictions_path.open("a", encoding="utf-8") as fh:
                for row in record_rows:
                    fh.write(row.model_dump_json() + "\n")

            n_correct_in_record = sum(1 for r in record_rows if r.correct)
            logger.info(
                f"[{idx + 1}/{len(records)}] {record.id} "
                f"turns={len(record_rows)} correct={n_correct_in_record}/{len(record_rows)}"
            )

        breakdown = summarize(
            rows,
            price_per_mtok_input=self._price_in,
            price_per_mtok_output=self._price_out,
        )
        summary = EvalSummary(
            split=split, seed=effective_seed, rows=rows, breakdown=breakdown
        )
        # `summary.json` excludes the per-row detail (that's in predictions.jsonl).
        summary_path.write_text(
            json.dumps(summary.model_dump(exclude={"rows"}), indent=2) + "\n",
            encoding="utf-8",
        )
        return summary

    def _select_records(
        self,
        split: str,
        *,
        n: int | None,
        record_id: str | None,
        seed: int,
    ) -> list[ConvFinQARecord]:
        records = self._repo.load_split(split)
        if record_id is not None:
            records = [r for r in records if r.id == record_id]
            if not records:
                raise KeyError(f"record id {record_id!r} not in split {split!r}")
            return records
        if n is not None and n < len(records):
            # Deterministic random sample — `--seed` makes runs reproducible
            # across days while still varying across seeds.
            records = random.Random(seed).sample(records, n)
        return records

    def _score_conversation(
        self,
        record: ConvFinQARecord,
        transcripts_path: Path,
        transcripts_md_path: Path,
    ) -> list[EvalRow]:
        calls = self._answerer.answer_conversation(record)[1]

        rows: list[EvalRow] = []
        for turn_idx, (call, question, gold) in enumerate(
            zip(
                calls,
                record.dialogue.conv_questions,
                record.dialogue.executed_answers,
                strict=True,
            )
        ):
            correct = compare_answer(
                call.predicted.answer,
                gold,
                unit=call.predicted.unit,
                tol_abs=self._tol_abs,
                tol_rel=self._tol_rel,
            )

            line = _build_transcript_line(
                record_id=record.id,
                turn_idx=turn_idx,
                question=question,
                call=call,
                gold=gold,
                correct=correct,
                latency_ms=call.latency_ms,
            )
            write_transcript(transcripts_path, line)
            write_transcript_md(transcripts_md_path, line)

            rows.append(
                EvalRow(
                    record_id=record.id,
                    turn_idx=turn_idx,
                    question=question,
                    predicted_answer=call.predicted.answer,
                    predicted_unit=call.predicted.unit,
                    predicted_calculation=call.predicted.calculation,
                    predicted_reasoning=call.predicted.reasoning,
                    gold=gold,
                    correct=correct,
                    latency_ms=call.latency_ms,
                    tokens_in=call.tokens_in,
                    tokens_out=call.tokens_out,
                    has_type2_question=record.features.has_type2_question,
                    has_duplicate_columns=record.features.has_duplicate_columns,
                    has_non_numeric_values=record.features.has_non_numeric_values,
                )
            )
        return rows


def _build_transcript_line(
    *,
    record_id: str,
    turn_idx: int,
    question: str,
    call: AnswerCall,
    gold: float | str,
    correct: bool,
    latency_ms: int,
) -> dict[str, Any]:
    """Self-contained replay record. Includes the full system prompt and
    raw response so a future debugger can re-run without the dataset.
    """
    tool_call = anthropic.extract_tool_call(call.raw_response)
    return {
        "record_id": record_id,
        "turn_idx": turn_idx,
        "question": question,
        "system_prompt": call.system_prompt,
        "messages": call.messages,
        "tool_call": tool_call,
        "parsed": call.predicted.model_dump(),
        "gold": gold,
        "correct": correct,
        "latency_ms": latency_ms,
        "raw_response": call.raw_response,
    }
