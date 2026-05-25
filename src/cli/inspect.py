"""`inspect` subcommand: replay one record's full dialogue and pretty-print each turn.

Lighter than `eval --record-id`: no run dir, no JSONL output, no breakdowns.
Uses the same `Answerer.answer_conversation` path so model behavior matches eval.
"""

import typer
from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.domain import ConvFinQARecord
from src.eval.metrics import compare_answer
from src.prompts.render import render_document
from src.repository.convfinqa import JsonDatasetRepository
from src.services.answer_service import AnswerService
from src.services.anthropic import AnthropicClient
from src.settings import Settings


def inspect_(
    record_id: str = typer.Argument(..., help="Record id, e.g. 'Single_JKHY/2009/page_28.pdf-3'."),
    split: str = typer.Option("train", "--split", help="Dataset split the record lives in."),
    show_doc: bool = typer.Option(
        True,
        "--show-doc/--no-show-doc",
        help="Print the record's pre-text, table, and post-text on entry — same as the model sees.",
    ),
) -> None:
    """Replay one record's dialogue and pretty-print predicted vs gold per turn."""
    settings = Settings()
    record = _load_record(settings, split, record_id)

    answer_service = AnswerService(llm=AnthropicClient(settings.anthropic))
    _, calls = answer_service.answer_conversation(record)

    console = Console()
    console.print(
        Panel.fit(
            f"[bold]{record.id}[/bold]    "
            f"split={split}  turns={record.features.num_dialogue_turns}  "
            f"type2={record.features.has_type2_question}",
            border_style="cyan",
        )
    )
    if show_doc:
        console.print("\n[bold]Document (as the model sees it)[/bold]")
        console.print(render_document(record.doc))

    n_correct = 0
    for turn_idx, (question, gold, call) in enumerate(
        zip(record.dialogue.conv_questions, record.dialogue.executed_answers, calls)
    ):
        p = call.predicted
        correct = compare_answer(p.answer, gold, unit=p.unit, tol_abs=settings.tol_abs, tol_rel=settings.tol_rel)
        n_correct += int(correct)

        mark = "[green]✓[/green]" if correct else "[red]✗[/red]"
        console.print(
            f"\n[bold cyan]t{turn_idx}[/bold cyan] {mark}  "
            f"[bold]Q:[/bold] {question}"
        )

        body = Table.grid(padding=(0, 1))
        body.add_column(style="dim", justify="right")
        body.add_column()
        body.add_row("predicted", f"[bold]{p.answer}[/bold]  (unit={p.unit})")
        body.add_row("gold", f"{gold!r}")
        body.add_row("reasoning", p.reasoning or "[dim]—[/dim]")
        body.add_row("tokens", f"{call.tokens_in:,} in / {call.tokens_out:,} out · {call.latency_ms} ms")
        console.print(body)

    n = len(calls)
    rich_print(
        f"\n[bold]per-turn:[/bold] {n_correct}/{n} = {n_correct / n:.1%}"
        if n
        else "\n[dim]no turns[/dim]"
    )


def _load_record(settings: Settings, split: str, record_id: str) -> ConvFinQARecord:
    records = JsonDatasetRepository(settings).load_split(split)
    for r in records:
        if r.id == record_id:
            return r
    raise typer.BadParameter(f"record {record_id!r} not found in split {split!r}")
