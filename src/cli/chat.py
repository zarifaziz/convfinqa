"""`chat` subcommand: free-form REPL over a single record.

Each user message becomes one LLM call with full prior-turn history replayed,
matching `eval` semantics. Type `exit` or `quit` (or Ctrl-D) to leave.
"""

import typer
from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel

from src.domain import ConvFinQARecord, Conversation
from src.prompts.render import render_document
from src.repository.convfinqa import JsonDatasetRepository
from src.services.answerer import Answerer
from src.services.llm_client import AnthropicClient
from src.settings import Settings


def chat_(
    record_id: str = typer.Argument(..., help="Record id, e.g. 'Single_JKHY/2009/page_28.pdf-3'."),
    split: str = typer.Option("train", "--split", help="Dataset split the record lives in."),
    show_doc: bool = typer.Option(
        True,
        "--show-doc/--no-show-doc",
        help="Print the record's pre-text, table, and post-text on entry — same as the model sees.",
    ),
) -> None:
    """Ask questions about a record in a REPL; history persists across turns."""
    settings = Settings()
    record = _load_record(settings, split, record_id)

    console = Console()
    console.print(
        Panel.fit(
            f"[bold]{record.id}[/bold]    "
            f"split={split}  turns={record.features.num_dialogue_turns}",
            border_style="cyan",
            title="chat",
        )
    )
    if show_doc:
        console.print("\n[bold]Document (as the model sees it)[/bold]")
        console.print(render_document(record.doc))
        console.print()

    answerer = Answerer(llm=AnthropicClient(settings.anthropic))
    conv = Conversation()

    while True:
        try:
            message = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            rich_print()
            break

        if message.strip().lower() in {"exit", "quit"}:
            break
        if not message.strip():
            continue

        turn, call = answerer.answer_turn(record.doc, conv.turns, message)
        conv.turns.append(turn)

        p = call.predicted
        rich_print(
            f"[blue][bold]assistant:[/bold] {p.answer}[/blue]  "
            f"[dim](unit={p.unit}, sign={p.sign_convention}, "
            f"{call.tokens_in:,}/{call.tokens_out:,} tok, {call.latency_ms} ms)[/dim]"
        )
        if p.calculation:
            rich_print(f"  [dim]calc:[/dim] {p.calculation}")
        if p.reasoning:
            rich_print(f"  [dim]why:[/dim]  {p.reasoning}")


def _load_record(settings: Settings, split: str, record_id: str) -> ConvFinQARecord:
    records = JsonDatasetRepository(settings).load_split(split)
    for r in records:
        if r.id == record_id:
            return r
    raise typer.BadParameter(f"record {record_id!r} not found in split {split!r}")
