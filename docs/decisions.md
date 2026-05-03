# Design Decisions

Five decisions worth defending in interview. Each is a queryable answer to "why did you do X?"

For the model-selection decision (Anthropic provider, primary model, dev-iteration model), see [model_selection.md](model_selection.md). It is kept separate because its rationale is benchmark-cited and the supporting evidence runs longer than this doc's per-entry budget.

## Single forced `submit_answer` tool over agentic calc-loop

Decision: one tool, one round-trip per turn. The model emits `{reasoning, calculation, answer, unit}` and the call ends.

Why: documents average ~675 tokens; multi-hop chains are short (median 2–3 ops in `turn_program`). A multi-step agent loop adds latency, cost, and a debug surface for a problem that does not need it. Forcing the tool also makes structured output reliable without regex over prose.

Alternative: agent loop exposing `calculate(expression)` (and optionally `lookup_table_cell(...)`), looping until `submit_answer`. Closer to a production agent shape.

Trigger to revisit: arithmetic-error bucket exceeds 15% of failures in error analysis, or calc-consistency rate (`eval(calculation) ≈ float(answer)`) drops below 90%.

## Full conversation replay over distilled state

Decision: each turn replays all prior `(user, q) → (assistant, tool_use) → (user, tool_result)` triples in the messages list. The document goes only in the system prompt.

Why: typical conversation is ~3.5 turns of single-line questions. Replay cost is trivial (~190 tokens per prior turn). Distillation introduces a state-tracking layer that drifts, costs more to debug, and gains nothing at this scale.

Alternative: maintain a running compressed "context summary" injected each turn instead of the full history.

Trigger to revisit: conversations grow to 20+ turns, or document size approaches Anthropic context limits. Neither applies to ConvFinQA as released.

## Hybrid tolerance: `max(tol_abs, tol_rel * |gold|)`

Decision: `compare_answer` uses `tol_abs=1e-4` and `tol_rel=5e-3` (0.5% relative), comparing as `abs(diff) <= max(tol_abs, tol_rel * |gold|)`.

Why: gold values span six orders of magnitude (e.g. `0.14136` and `206588`). A flat `1e-3` absolute would be 10% relative on the small percent and absurdly tight on the integer. Display rounding (gold `0.14136` vs predicted `"14.1%"` → 0.141, diff 3.6e-4) needs the relative term; near-zero golds need the absolute term.

Alternative: pure absolute tolerance, or pure relative.

Trigger to revisit: error analysis shows "format-correct, slightly off" as the dominant failure bucket — tighten or loosen `tol_rel` and re-run.

## Dev as held-out, no test split in the file

Decision: report dev accuracy as the headline. State explicitly in `REPORT.md` that dev is also the iteration set, so the headline is not a true held-out estimate.

Why: the dataset card advertises a 434-record test split that is not present in the shipped JSON. Pretending otherwise would mislead. Carving a final held-out slice from train would shrink the few-shot pool and add methodology overhead disproportionate to a 15-hour prototype.

Alternative: carve ~100 records from train as a final held-out set; iterate on dev; report on the held-out.

Trigger to revisit: result is published as a benchmark claim rather than a take-home prototype.

## No data cleaning over preemptive normalization

Decision: pass `doc.table`, `doc.pre_text`, `doc.post_text`, and `dialogue.*` to the model as-is. No coercion of `'-'`, `'n/a'`, `'( in thousands )'`, `'yes'`/`'no'`. No collapsing of `(1)`/`(2)` column suffixes.

Why: empirical investigation across 3,458 records (see [plans/2_data_loading_and_cleaning_policy.md](../plans/2_data_loading_and_cleaning_policy.md)) showed the residue patterns are semantically meaningful, not dirty. `'-'` and `'n/a'` are "no value reported" markers — coercing to `0` changes meaning. `'( in thousands )'` is a unit hint the model uses. `(1)`/`(2)` suffixes mark genuinely distinct source columns (typically reported vs restated figures).

Alternative: preemptive coercion of non-numeric cells and suffix collapsing.

Trigger to revisit: eval accuracy on records where `has_non_numeric_values=True` or `has_duplicate_columns=True` is materially lower than on the rest of dev — handle those subgroups specifically rather than across-the-board.
