"""Typer CLI for the ConvFinQA pipeline.

Thin entry point: parse args, build services, call `Evaluator.run`, print
summary. All orchestration lives in `src/services/evaluator.py`.

Phase 2 is single-turn only (turn 0 of each record); multi-turn replay
lands in Phase 3.
"""

from typing import Optional

import typer
from loguru import logger
from rich import print as rich_print
from rich.console import Console
from rich.table import Table

from src.logger import init_run
from src.repository.convfinqa import JsonDatasetRepository
from src.services.answerer import Answerer
from src.services.evaluator import EvalSummary, Evaluator
from src.services.llm_client import AnthropicClient
from src.settings import Settings

app = typer.Typer(
    name="main",
    help="ConvFinQA pipeline CLI.",
    add_completion=True,
    no_args_is_help=False,
)


@app.command()
def eval(
    n: Optional[int] = typer.Option(None, "--n", help="Cap evaluation to N randomly-sampled records (no cap if omitted)."),
    record_id: Optional[str] = typer.Option(None, "--record-id", help="Run a single record by id."),
    split: str = typer.Option("dev", "--split", help="Dataset split to evaluate on."),
    seed: Optional[int] = typer.Option(None, "--seed", help="RNG seed for sampling. If omitted, a fresh seed is generated and logged."),
) -> None:
    """Score the first-turn predictions over `split`."""
    settings = Settings()
    run_dir = init_run(settings)
    logger.info(f"run dir: {run_dir}")

    evaluator = Evaluator(
        repo=JsonDatasetRepository(settings),
        answerer=Answerer(llm=AnthropicClient(settings.anthropic)),
        tol_abs=settings.tol_abs,
        tol_rel=settings.tol_rel,
    )
    summary = evaluator.run(
        split=split, run_dir=run_dir, n=n, record_id=record_id, seed=seed
    )
    _print_summary_table(summary)


def _print_summary_table(summary: EvalSummary) -> None:
    console = Console()
    table = Table(title=f"first-turn eval on {summary.split!r}")
    table.add_column("record_id", style="cyan", no_wrap=False)
    table.add_column("predicted", style="white")
    table.add_column("gold", style="white")
    table.add_column("correct", style="green")
    table.add_column("ms", style="dim", justify="right")
    for row in summary.rows:
        table.add_row(
            row.record_id,
            f"{row.predicted_answer} ({row.predicted_unit})",
            str(row.gold),
            "yes" if row.correct else "no",
            str(row.latency_ms),
        )
    console.print(table)
    rich_print(
        f"[bold]accuracy:[/bold] {summary.n_correct}/{summary.n_records} "
        f"= {summary.accuracy:.1%}"
    )


if __name__ == "__main__":
    app()
