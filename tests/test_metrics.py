import pytest

from src.eval.metrics import compare_answer


@pytest.mark.parametrize(
    ("predicted", "gold", "expected"),
    [
        ("14.1%", 0.14136, True),
        ("142.4%", 1.42403, True),
        # 14.0 vs 0.14136 -> diff 0.00136, threshold max(1e-4, 5e-3 * 0.14136) = 7.07e-4
        ("14.0%", 0.14136, False),
        ("206588", 206588.0, True),
        ("206589", 206588.0, True),
        ("$25,587", 25587.0, True),
        ("(1,234)", -1234.0, True),
        (0.141, 0.14136, True),
        # unitless string predictions must not auto-promote from percent
        ("14.1", 0.14136, False),
        ("not a number", 1.0, False),
    ],
)
def test_compare_answer_numeric(
    predicted: str | int | float, gold: float, expected: bool
) -> None:
    assert compare_answer(predicted, gold) is expected


@pytest.mark.parametrize(
    ("predicted", "gold", "expected"),
    [
        ("yes", "yes", True),
        ("YES", "yes", True),
        (" yes ", "yes", True),
        ("no", "yes", False),
    ],
)
def test_compare_answer_string(predicted: str, gold: str, expected: bool) -> None:
    assert compare_answer(predicted, gold) is expected


@pytest.mark.parametrize(
    ("predicted", "gold", "unit", "expected"),
    [
        # Real Phase 2 failure: model emitted "73.11" with unit="percent",
        # gold was the decimal 0.73109. Should be normalized via the unit hint.
        ("73.11", 0.73109, "percent", True),
        ("14.1", 0.14136, "percent", True),
        # `%` suffix takes precedence — no double-division.
        ("14.1%", 0.14136, "percent", True),
        # Non-percent unit: don't divide.
        ("206588", 206588.0, "raw", True),
        ("206588", 206588.0, "none", True),
        # Falls back to current behavior when unit is omitted.
        ("14.1", 0.14136, None, False),
        # Real Phase 4 failure: dataset stores some percent golds in raw-percent
        # form (3.97 for a 3.97% discount rate), not decimal (0.0397). Try both
        # interpretations and accept whichever matches.
        ("3.97", 3.97, "percent", True),
        ("-9402", -9402.0, "percent", True),
    ],
)
def test_compare_answer_honors_unit_hint(
    predicted: str, gold: float, unit: str | None, expected: bool
) -> None:
    assert compare_answer(predicted, gold, unit=unit) is expected
