"""Unit tests for Statutory Citation Normalizer (Constitution Principle VII)."""

from eios.aml.statutory_normalizer import StatutoryCitationNormalizer


def test_statutory_normalizer_detects_citations() -> None:
    normalizer = StatutoryCitationNormalizer()
    text = (
        "Client activity reviewed under 31 CFR 1010.410 and 31 U.S.C. 5318(g). "
        "Further inquiries initiated pursuant to Section 314(b) of the USA PATRIOT Act."
    )

    citations = normalizer.extract_citations(text)
    codes = [c.normalized_code for c in citations]

    assert "31_CFR_1010" in codes
    assert "31_USC_5318" in codes
    assert "SECTION_314" in codes


def test_statutory_normalizer_replaces_for_audit() -> None:
    normalizer = StatutoryCitationNormalizer()
    text = "Report filed pursuant to 31 CFR 1010 regarding suspicious volume."
    audit_text = normalizer.normalize_text_for_audit(text)

    assert "[STATUTE:31_CFR_1010]" in audit_text
