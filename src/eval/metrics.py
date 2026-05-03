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
    tol_abs: float = 1e-4,
    tol_rel: float = 5e-3,
) -> bool:
    if isinstance(gold, str):
        return str(predicted).strip().lower() == gold.strip().lower()

    # bool subclasses int — reject so True != 1.0 here.
    if isinstance(predicted, bool):
        return False
    if isinstance(predicted, (int, float)):
        parsed: float | None = float(predicted)
    elif isinstance(predicted, str):
        parsed = _parse_numeric(predicted)
    else:
        return False

    if parsed is None:
        return False

    return abs(parsed - gold) <= max(tol_abs, tol_rel * abs(gold))
