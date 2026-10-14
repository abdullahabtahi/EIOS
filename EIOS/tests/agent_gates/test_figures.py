"""Figure extraction and normalisation tests (T015). Designed from the units and shapes operators write."""

import pytest

from eios.agent_gates.core.figures import extract_figures


def _one(text: str):  # type: ignore[no-untyped-def]
    figures = extract_figures(text)
    assert len(figures) == 1, [f.text for f in figures]
    return figures[0]


@pytest.mark.parametrize(
    ("text", "value", "unit"),
    [
        ("Revenue is $3,820,000.", 3_820_000.0, "currency"),
        ("It cost USD 500 today.", 500.0, "currency"),
        ("About $3.8 million.", 3_800_000.0, "currency"),
        ("Revenue 3.82M USD.", 3_820_000.0, "currency"),
        ("A budget of 500k dollars.", 500_000.0, "currency"),
        ("Volume of 2bn dollars.", 2_000_000_000.0, "currency"),
        ("The hazard is 78%.", 78.0, "percent"),
        ("The hazard is 78 percent.", 78.0, "percent"),
        ("Login fell by -68%.", -68.0, "percent"),
        ("A spread of 1.2 bps.", 1.2, "bps"),
        ("A 16.0x multiplier.", 16.0, "multiplier"),
        ("That is 16 times income.", 16.0, "multiplier"),
        ("An SLA of 4.8 hrs.", 4.8, "duration"),
        ("The ring has 23 accounts.", 23.0, "none"),
    ],
)
def test_numbers_and_units_are_normalised(text: str, value: float, unit: str) -> None:
    figure = _one(text)
    assert figure.value == pytest.approx(value)
    assert figure.unit == unit


def test_basis_points_are_not_billions() -> None:
    figure = _one("A spread move of 1.2 bps.")
    assert figure.unit == "bps"
    assert figure.value == pytest.approx(1.2)


@pytest.mark.parametrize(
    ("text", "value", "tolerance"),
    [
        ("About $3.8 million.", 3_800_000.0, 50_000.0),
        ("Exactly $3,820,000.", 3_820_000.0, 0.5),
        ("A hazard of 78.4%.", 78.4, 0.05),
    ],
)
def test_tolerance_is_half_the_last_stated_digit(text: str, value: float, tolerance: float) -> None:
    figure = _one(text)
    assert figure.value == pytest.approx(value)
    assert figure.tolerance == pytest.approx(tolerance)


@pytest.mark.parametrize(
    ("text", "value", "tolerance"),
    [
        ("sixteen accounts", 16.0, 0.5),
        ("twenty-three accounts", 23.0, 0.5),
        ("about three million dollars", 3_000_000.0, 500_000.0),
        ("two hundred and fifty items sold", 250.0, 0.5),
        ("one million dollars", 1_000_000.0, 500_000.0),
        ("four billion", 4_000_000_000.0, 500_000_000.0),
    ],
)
def test_spelled_out_numbers_are_figures(text: str, value: float, tolerance: float) -> None:
    figure = _one(text)
    assert figure.value == pytest.approx(value)
    assert figure.tolerance == pytest.approx(tolerance)


def test_a_lone_one_is_prose_not_a_figure() -> None:
    assert extract_figures("One of the accounts is flagged.") == []


@pytest.mark.parametrize(
    ("text", "period"),
    [
        ("Income was $500 per week.", "week"),
        ("Income was $500 monthly.", "month"),
        ("About 40 trades daily.", "day"),
        ("Fees of $9,000 per year.", "year"),
        ("Income was $500.", None),
    ],
)
def test_period_qualifiers_are_captured(text: str, period: str | None) -> None:
    assert _one(text).period == period


def test_context_words_surround_the_figure() -> None:
    figure = _one("The composite risk score of the account is 16 today.")
    assert {"composite", "risk", "score"} <= set(figure.context)
    assert "the" not in figure.context


def test_masked_spans_are_not_figures() -> None:
    text = "Account CR84920 has 23 accounts."
    start = text.index("CR84920")
    figures = extract_figures(text, masked=[(start, start + len("CR84920"))])
    assert [f.value for f in figures] == [23.0]


def test_ids_inside_words_are_not_figures() -> None:
    assert extract_figures("See ticket abc123 for details.") == []
