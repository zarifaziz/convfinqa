"""`dump-failures` subcommand — surface failed predictions for hand-classification.

Reads `predictions.jsonl` from a run dir, joins each failed turn back to its
source record (for prior turns + table), and writes `<run>/failures.md`. One
section per failure, sorted by (record num_dialogue_turns desc, turn_idx desc)
so the hardest cases group together.
"""

import json
from pathlib import Path

import typer

from src.domain import ConvFinQARecord
from src.prompts.render import render_table
from src.repository.convfinqa import JsonDatasetRepository
from src.settings import Settings


def dump_failures(
    run_dir: Path = typer.Argument(..., help="Path to runs/<timestamp>/."),
    split: str = typer.Option(
        "train",
        "--split",
        help="Dataset split the run was over.",
    ),
) -> None:
    """Write `<run_dir>/failures.md` from the run's predictions.jsonl."""
    predictions_path = run_dir / "predictions.jsonl"
    if not predictions_path.is_file():
        raise typer.BadParameter(f"missing {predictions_path}")

    settings = Settings()
    records = {r.id: r for r in JsonDatasetRepository(settings).load_split(split)}

    failures = [
        json.loads(line)
        for line in predictions_path.read_text(encoding="utf-8").splitlines()
        if line and not json.loads(line)["correct"]
    ]

    failures.sort(
        key=lambda f: (
            -records[f["record_id"]].features.num_dialogue_turns,
            -f["turn_idx"],
        )
    )

    out_path = run_dir / "failures.md"
    with out_path.open("w", encoding="utf-8") as fh:
        fh.write(_header(failures, predictions_path))
        for failure in failures:
            fh.write(_render_failure(failure, records[failure["record_id"]]))

    typer.echo(f"wrote {out_path} — {len(failures)} failures")


def _header(failures: list[dict], src: Path) -> str:
    return (
        f"# Failures from {src}\n\n"
        f"{len(failures)} failed turns. Sorted by "
        f"`(num_dialogue_turns desc, turn_idx desc)` — hardest cases first.\n\n"
        f"---\n\n"
    )


def _render_failure(failure: dict, record: ConvFinQARecord) -> str:
    turn_idx = failure["turn_idx"]
    questions = record.dialogue.conv_questions
    golds = record.dialogue.executed_answers

    prior_block = "\n".join(
        f"- t{i}: {questions[i]!r} → gold `{golds[i]!r}`"
        for i in range(turn_idx)
    ) or "_none_"

    return (
        f"## {record.id} — turn {turn_idx}\n\n"
        f"**features:** num_turns={record.features.num_dialogue_turns}, "
        f"type2={record.features.has_type2_question}, "
        f"dup_cols={record.features.has_duplicate_columns}, "
        f"non_numeric={record.features.has_non_numeric_values}\n\n"
        f"**Prior turns:**\n{prior_block}\n\n"
        f"**This turn (t{turn_idx}):** {failure['question']!r}\n\n"
        f"- **gold:** `{failure['gold']!r}`\n"
        f"- **predicted:** `{failure['predicted_answer']}` (unit `{failure['predicted_unit']}`, "
        f"sign `{failure.get('predicted_sign_convention', '?')}`)\n"
        f"- **calculation:** `{failure['predicted_calculation']}`\n"
        f"- **reasoning:** {failure['predicted_reasoning']}\n\n"
        f"**Table:**\n\n{render_table(record.doc.table)}\n\n"
        f"---\n\n"
    )
