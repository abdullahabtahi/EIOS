"""Test Metric Auditor Gate Number Normalizer and Token Extractor (T032)."""

from eios.ontology.auditor.normalizer import NumericTokenNormalizer


def test_numeric_token_extraction_and_normalization():
    normalizer = NumericTokenNormalizer()
    text = "Partner 8821 generated $142,500 across 38 clients with a 15% conversion rate."
    tokens = normalizer.extract_numbers(text)

    values = [t.normalized_value for t in tokens]
    # Expect 142500.0, 38.0, 0.15
    assert 142500.0 in values
    assert 38.0 in values
    assert 0.15 in values


def test_magnitude_suffix_parsing():
    normalizer = NumericTokenNormalizer()
    text = "Total volume reached $1.5M with 250k transactions and 10B volume."
    tokens = normalizer.extract_numbers(text)

    val_map = {t.raw_string: t.normalized_value for t in tokens}
    assert val_map["$1.5M"] == 1500000.0
    assert val_map["250k"] == 250000.0
    assert val_map["10B"] == 10000000000.0


def test_calendar_and_citation_exclusions():
    normalizer = NumericTokenNormalizer()
    text = "On March 15, 2026, we inspected client [1] and [EVID-102]. 1. Step one."
    tokens = normalizer.extract_numbers(text)

    # 15, 2026, [1], 1. should be filtered out by context-aware rules
    values = [t.normalized_value for t in tokens]
    assert 2026.0 not in values
    assert 15.0 not in values
    assert len(tokens) == 0


def test_statutory_and_regulatory_citation_exclusions():
    normalizer = NumericTokenNormalizer()
    text = (
        "Pursuant to Section 314(b) of the USA PATRIOT Act and 31 CFR 1010.311, "
        "Form 111 was submitted with suspicious volume of $45,000.00."
    )
    tokens = normalizer.extract_numbers(text)
    values = [t.normalized_value for t in tokens]

    # Only the dollar metric 45000.0 should be extracted; statutory numbers must be excluded
    assert 45000.0 in values
    assert 314.0 not in values
    assert 111.0 not in values
    assert len(tokens) == 1
