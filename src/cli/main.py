"""Typer CLI for the ConvFinQA pipeline.

Subcommands:
  - `eval` — score the model on a dataset split (full pipeline).
  - `inspect` — replay one record's dialogue and pretty-print each turn.
  - `chat` — free-form REPL over a single record (history preserved).
  - `dump-failures` — turn a run's failed predictions into hand-readable markdown.
  - `plot-results` — render report charts from a run's summary.json.
"""

import typer

from src.cli.chat import chat_
from src.cli.eval import eval_
from src.cli.inspect import inspect_
from src.cli.scripts import dump_failures, plot_results

app = typer.Typer(
    name="main",
    help="ConvFinQA pipeline CLI.",
    add_completion=True,
    no_args_is_help=True,
)

app.command(name="eval")(eval_)
app.command(name="inspect")(inspect_)
app.command(name="chat")(chat_)
app.command(name="dump-failures")(dump_failures)
app.command(name="plot-results")(plot_results)


if __name__ == "__main__":
    app()
