"""`eval` subcommand: score the model on a dataset split (full pipeline)."""

from typing import Optional

import typer
from loguru import logger
from rich import print as rich_print
from rich.console import Console
from rich.table import Table

from src.logger import init_run
from src.repository.convfinqa import JsonDatasetRepository
from src.services.answer_service import AnswerService
from src.services.anthropic import AnthropicClient
from src.services.evaluation_service import EvalSummary, EvaluationService
from src.settings import Settings


def eval_(
    n: Optional[int] = typer.Option(
        None,
        "--n",
        help="Cap evaluation to N randomly-sampled records (no cap if omitted).",
    ),
    record_id: Optional[str] = typer.Option(
        None, "--record-id", help="Run a single record by id."
    ),
    split: str = typer.Option(
        "train",
        "--split",
        help=(
            "Dataset split to evaluate on. Default 'train' is the iteration "
            "set; 'dev' is the held-out measurement set, used only for the "
            "tagged prompt-v0 / prompt-v1 / prompt-v2 measurement runs."
        ),
    ),
    seed: Optional[int] = typer.Option(
        None,
        "--seed",
        help="RNG seed for sampling. If omitted, a fresh seed is generated and logged.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Print every per-turn row in the summary table."
    ),
    concurrency: int = typer.Option(
        15,
        "--concurrency",
        help=(
            "Number of records evaluated in parallel. 1 disables threading. "
            "15 sits at ~50% of Anthropic's 450k input-tok/min ceiling at "
            "~4k tok/call avg, leaving retry headroom."
        ),
    ),
) -> None:
    """Score the model's predictions over `split`, multi-turn."""
    settings = Settings()
    run_dir = init_run(settings)
    logger.info(f"run dir: {run_dir}")

    evaluation_service = EvaluationService(
        repo=JsonDatasetRepository(settings),
        answer_service=AnswerService(llm=AnthropicClient(settings.anthropic)),
        tol_abs=settings.tol_abs,
        tol_rel=settings.tol_rel,
        price_per_mtok_input=settings.anthropic.price_per_mtok_input,
        price_per_mtok_output=settings.anthropic.price_per_mtok_output,
    )
    summary = evaluation_service.run(
        split=split,
        run_dir=run_dir,
        n=n,
        record_id=record_id,
        seed=seed,
        concurrency=concurrency,
    )
    _print_summary(summary, verbose=verbose)


def _print_summary(summary: EvalSummary, *, verbose: bool) -> None:
    console = Console()

    if verbose:
        table = Table(title=f"per-turn eval on {summary.split!r}")
        table.add_column("record_id", style="cyan", no_wrap=False)
        table.add_column("turn", style="dim", justify="right")
        table.add_column("predicted", style="white")
        table.add_column("gold", style="white")
        table.add_column("correct", style="green")
        for row in summary.rows:
            table.add_row(
                row.record_id,
                str(row.turn_idx),
                f"{row.predicted_answer} ({row.predicted_unit})",
                str(row.gold),
                "yes" if row.correct else "no",
            )
        console.print(table)

    b = summary.breakdown
    pt = b["per_turn_accuracy"]
    pc = b["per_conversation_accuracy"]
    rich_print(
        f"[bold]per-turn:[/bold] {pt['correct']}/{pt['n']} = {pt['accuracy']:.1%}    "
        f"[bold]per-conversation:[/bold] {pc['correct']}/{pc['n']} = {pc['accuracy']:.1%}"
    )
    rich_print(
        f"[bold]by turn idx:[/bold] {_fmt_rate_curve(b['per_turn_idx_accuracy'])}"
    )
    rich_print(
        f"[bold]conditional P(correct|prev correct):[/bold] "
        f"{_fmt_rate_curve(b['conditional_accuracy'])}"
    )

    qt = b["accuracy_by_question_type"]
    fmt = b["accuracy_by_gold_format"]
    rich_print(
        f"[bold]by type:[/bold] type_i={_fmt_rate(qt['type_i'])}  "
        f"type_ii={_fmt_rate(qt['type_ii'])}    "
        f"[bold]by gold:[/bold] numeric={_fmt_rate(fmt['numeric'])}  "
        f"boolean={_fmt_rate(fmt['boolean'])}"
    )

    cost = b["cost"]
    rich_print(
        f"[bold]cost:[/bold] {cost['tokens_in_total']:,} in + {cost['tokens_out_total']:,} out tokens "
        f"≈ ${cost['usd_estimate']:.4f}    "
        f"[bold]wall:[/bold] {cost['total_seconds']:.1f}s"
    )


def _fmt_rate(rate: dict) -> str:
    acc = rate["accuracy"]
    if acc is None:
        return f"n/a (n={rate['n']})"
    return f"{acc:.1%} (n={rate['n']})"


def _fmt_rate_curve(curve: dict[str, dict]) -> str:
    return "  ".join(f"t{idx}={_fmt_rate(rate)}" for idx, rate in curve.items())
