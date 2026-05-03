"""Evaluator service.

Owns the load → answer → score → write loop. Depends on the
`DatasetRepository` Protocol (not the concrete JSON repo) and an `Answerer`,
so it's testable with a fake repo + fake LLM client.

Writes three sibling files in the run dir:
  - `transcripts.jsonl` — one line per LLM call, full system_prompt /
    messages / tool_call / parsed for replay.
  - `predictions.jsonl` — one line per turn, lightweight grading record.
  - `summary.json` — overall accuracy.
"""

import json
import random
import time
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel

from src.domain import ConvFinQARecord
from src.eval.metrics import compare_answer
from src.repository.convfinqa import DatasetRepository
from src.services.answerer import Answerer, AnswerCall
from src.services.transcripts import write_transcript, write_transcript_md


class EvalRow(BaseModel):
    record_id: str
    turn_idx: int
    question: str
    predicted_answer: str
    predicted_unit: str
    gold: float | str
    correct: bool
    latency_ms: int


class EvalSummary(BaseModel):
    split: str
    n_records: int
    n_correct: int
    accuracy: float
    seed: int | None = None
    rows: list[EvalRow]


class Evaluator:
    def __init__(
        self,
        repo: DatasetRepository,
        answerer: Answerer,
        tol_abs: float,
        tol_rel: float,
    ) -> None:
        self._repo = repo
        self._answerer = answerer
        self._tol_abs = tol_abs
        self._tol_rel = tol_rel

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

        logger.info(f"evaluating {len(records)} record(s) on split={split!r} (turn 0 only)")

        rows: list[EvalRow] = []
        for idx, record in enumerate(records):
            row = self._score_first_turn(record, transcripts_path, transcripts_md_path)
            rows.append(row)
            with predictions_path.open("a", encoding="utf-8") as fh:
                fh.write(row.model_dump_json() + "\n")
            logger.info(
                f"[{idx + 1}/{len(records)}] {record.id} "
                f"pred={row.predicted_answer!r} gold={row.gold!r} "
                f"correct={row.correct} ({row.latency_ms} ms)"
            )

        n_correct = sum(1 for r in rows if r.correct)
        summary = EvalSummary(
            split=split,
            n_records=len(rows),
            n_correct=n_correct,
            accuracy=n_correct / len(rows) if rows else 0.0,
            seed=effective_seed,
            rows=rows,
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

    def _score_first_turn(
        self,
        record: ConvFinQARecord,
        transcripts_path: Path,
        transcripts_md_path: Path,
    ) -> EvalRow:
        question = record.dialogue.conv_questions[0]
        gold = record.dialogue.executed_answers[0]

        t0 = time.perf_counter()
        call = self._answerer.answer_single(record.doc, question)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        correct = compare_answer(
            call.predicted.answer, gold, tol_abs=self._tol_abs, tol_rel=self._tol_rel
        )

        line = _build_transcript_line(
            record_id=record.id,
            turn_idx=0,
            question=question,
            call=call,
            gold=gold,
            correct=correct,
            latency_ms=latency_ms,
        )
        write_transcript(transcripts_path, line)
        write_transcript_md(transcripts_md_path, line)

        return EvalRow(
            record_id=record.id,
            turn_idx=0,
            question=question,
            predicted_answer=call.predicted.answer,
            predicted_unit=call.predicted.unit,
            gold=gold,
            correct=correct,
            latency_ms=latency_ms,
        )


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
    tool_call = _extract_tool_call(call.raw_response)
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


def _extract_tool_call(raw_response: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the `tool_use` block out of an Anthropic response dump."""
    for block in raw_response.get("content", []) or []:
        if block.get("type") == "tool_use":
            return {"name": block.get("name"), "input": block.get("input")}
    return None
