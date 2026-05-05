"""Auxiliary CLI subcommands: failure surfacing + result plotting."""

from __future__ import annotations

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
        fh.write(_failures_header(failures, predictions_path))
        for failure in failures:
            fh.write(_render_failure(failure, records[failure["record_id"]]))

    typer.echo(f"wrote {out_path} — {len(failures)} failures")


def plot_results(
    summary_path: Path = typer.Argument(
        ..., help="Path to runs/<timestamp>/summary.json."
    ),
    out_dir: Path = typer.Option(
        Path("figures"), "--out-dir", help="Where to write PNGs."
    ),
) -> None:
    """Render the report charts from a run's summary.json."""
    if not summary_path.is_file():
        raise typer.BadParameter(f"missing {summary_path}")

    import matplotlib.pyplot as plt  # noqa: F401 — imported lazily; heavy dep

    summary = json.loads(summary_path.read_text())
    out_dir.mkdir(parents=True, exist_ok=True)
    _apply_style()

    _accuracy_by_turn(summary, out_dir / "accuracy_by_turn.png")
    _breakdowns(summary, out_dir / "breakdowns.png")
    _tokens_by_turn(summary, out_dir / "tokens_by_turn.png")
    typer.echo(
        f"wrote {out_dir}/accuracy_by_turn.png, breakdowns.png, tokens_by_turn.png"
    )


# Failures rendering ---------------------------------------------------------


def _failures_header(failures: list[dict], src: Path) -> str:
    return f"""\
# Failures from {src}

{len(failures)} failed turns. Sorted by `(num_dialogue_turns desc, turn_idx desc)` — hardest cases first.

---

"""


def _render_failure(failure: dict, record: ConvFinQARecord) -> str:
    turn_idx = failure["turn_idx"]
    questions = record.dialogue.conv_questions
    golds = record.dialogue.executed_answers

    prior_block = (
        "\n".join(
            f"- t{i}: {questions[i]!r} → gold `{golds[i]!r}`" for i in range(turn_idx)
        )
        or "_none_"
    )

    feats = record.features
    return f"""\
## {record.id} — turn {turn_idx}

**features:** num_turns={feats.num_dialogue_turns}, type2={feats.has_type2_question}, dup_cols={feats.has_duplicate_columns}, non_numeric={feats.has_non_numeric_values}

**Prior turns:**
{prior_block}

**This turn (t{turn_idx}):** {failure["question"]!r}

- **gold:** `{failure["gold"]!r}`
- **predicted:** `{failure["predicted_answer"]}` (unit `{failure["predicted_unit"]}`, sign `{failure.get("predicted_sign_convention", "?")}`)
- **calculation:** `{failure["predicted_calculation"]}`
- **reasoning:** {failure["predicted_reasoning"]}

**Table:**

{render_table(record.doc.table)}

---

"""


# Plotting -------------------------------------------------------------------

_NAVY = "#1f3a5f"
_ORANGE = "#d97706"
_GREY = "#6b7280"
_LIGHT = "#e5e7eb"


def _apply_style() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": _GREY,
            "axes.labelcolor": "#111827",
            "xtick.color": _GREY,
            "ytick.color": _GREY,
            "axes.grid": True,
            "grid.color": _LIGHT,
            "grid.linewidth": 0.6,
            "figure.dpi": 140,
        }
    )


def _accuracy_by_turn(summary: dict, out: Path) -> None:
    import matplotlib.pyplot as plt

    breakdown = summary["breakdown"]
    per_turn = breakdown["per_turn_idx_accuracy"]
    cond = breakdown["conditional_accuracy"]

    indices = sorted(int(k) for k in per_turn.keys() if per_turn[k]["n"] >= 5)
    marginal_y = [per_turn[str(i)]["accuracy"] for i in indices]
    marginal_n = [per_turn[str(i)]["n"] for i in indices]

    cond_indices = [i for i in indices if str(i) in cond and cond[str(i)]["n"] >= 5]
    cond_y = [cond[str(i)]["accuracy"] for i in cond_indices]
    cond_n = [cond[str(i)]["n"] for i in cond_indices]

    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.plot(
        cond_indices, cond_y,
        marker="s", color=_ORANGE, linewidth=2.2,
        label=r"Conditional $P(t_i \text{ correct} \mid t_{i-1} \text{ correct})$",
    )
    ax.plot(
        indices, marginal_y,
        marker="o", color=_NAVY, linewidth=2.2,
        label="Marginal accuracy at turn $i$",
    )
    for i, y, n in zip(indices, marginal_y, marginal_n):
        ax.annotate(f"n={n}", (i, y - 0.04), ha="center", fontsize=8, color=_GREY)
    for i, y, n in zip(cond_indices, cond_y, cond_n):
        ax.annotate(f"n={n}", (i, y + 0.025), ha="center", fontsize=8, color=_GREY)

    ax.set_xlabel("Turn index")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0.7, 1.0)
    ax.set_xticks(indices)
    ax.legend(loc="lower left", frameon=False)
    ax.set_title("No late-turn collapse — both curves flat across conversation depth")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def _breakdowns(summary: dict, out: Path) -> None:
    import matplotlib.pyplot as plt

    bd = summary["breakdown"]
    rows = [
        ("Type I", bd["accuracy_by_question_type"]["type_i"]),
        ("Type II", bd["accuracy_by_question_type"]["type_ii"]),
        ("Numeric gold", bd["accuracy_by_gold_format"]["numeric"]),
        ("Boolean gold", bd["accuracy_by_gold_format"]["boolean"]),
        (
            "has_duplicate_columns=True",
            bd["accuracy_by_doc_feature"]["has_duplicate_columns"]["true"],
        ),
        (
            "has_non_numeric_values=True",
            bd["accuracy_by_doc_feature"]["has_non_numeric_values"]["true"],
        ),
    ]
    labels = [r[0] for r in rows]
    values = [r[1]["accuracy"] for r in rows]
    ns = [r[1]["n"] for r in rows]

    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    bars = ax.barh(
        list(reversed(labels)),
        list(reversed(values)),
        color=_NAVY, edgecolor="white",
    )
    for bar, n, val in zip(bars, list(reversed(ns)), list(reversed(values))):
        ax.text(
            val + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val:.1%}  (n={n})",
            va="center", fontsize=9, color="#111827",
        )
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Per-turn accuracy")
    ax.set_title("Accuracy by breakdown axis (full dev)")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def _tokens_by_turn(summary: dict, out: Path) -> None:
    import matplotlib.pyplot as plt

    cost = summary["breakdown"]["cost"]
    per_turn = summary["breakdown"]["per_turn_idx_accuracy"]
    tokens = cost["mean_tokens_in_by_turn_idx"]
    indices = [
        i for i in sorted(int(k) for k in tokens.keys()) if per_turn[str(i)]["n"] >= 5
    ]
    y = [tokens[str(i)] for i in indices]

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.plot(indices, y, marker="o", color=_NAVY, linewidth=2.2)
    ax.fill_between(indices, [y[0]] * len(indices), y, color=_NAVY, alpha=0.08)
    for i, v in zip(indices, y):
        ax.annotate(
            f"{v / 1000:.1f}k", (i, v),
            textcoords="offset points", xytext=(0, 8),
            ha="center", fontsize=9, color=_GREY,
        )
    ax.set_xlabel("Turn index")
    ax.set_ylabel("Mean input tokens / call")
    ax.set_xticks(indices)
    ax.set_title("Input tokens grow with conversation depth — caching headroom")
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
