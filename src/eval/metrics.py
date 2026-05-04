"""Compare a model-emitted answer against a gold value within tolerance."""


def _parse_numeric(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1].strip()

    if text.startswith("$"):
        text = text[1:].strip()
    text = text.replace(",", "")

    try:
        parsed = float(text)
    except ValueError:
        return None

    if is_percent:
        parsed /= 100.0
    if negative:
        parsed = -parsed
    return parsed


def compare_answer(
    predicted: str | int | float,
    gold: float | str,
    unit: str | None = None,
    tol_abs: float = 1e-4,
    tol_rel: float = 5e-3,
) -> bool:
    if isinstance(gold, str):
        return str(predicted).strip().lower() == gold.strip().lower()

    # bool subclasses int — reject so True != 1.0 here.
    if isinstance(predicted, bool):
        return False
    if isinstance(predicted, (int, float)):
        candidates: list[float] = [float(predicted)]
    elif isinstance(predicted, str):
        parsed = _parse_numeric(predicted)
        if parsed is None:
            return False
        candidates = [parsed]
        # Percent unit, no `%` suffix: try both raw-percent (3.97 = 3.97%) and
        # decimal-normalized (3.97 → 0.0397) against gold. The dataset stores
        # percent golds in BOTH conventions — some as decimal (0.141), some as
        # raw-percent (3.97 for a 3.97% discount rate). Try both, accept the
        # closer match within tolerance.
        if unit == "percent" and not predicted.strip().endswith("%"):
            candidates.append(parsed / 100.0)
    else:
        return False

    threshold = max(tol_abs, tol_rel * abs(gold))
    return any(abs(c - gold) <= threshold for c in candidates)
