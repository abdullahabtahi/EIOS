from eios.reference.tiers import OFFSHORE_CENTRE_MIN_ENTITIES, jurisdiction_tiers

PAYLOAD = {
    "countries": [
        {"iso2": "MM", "fatf_list": "call_for_action", "entities_incorporated": None},
        {"iso2": "VN", "fatf_list": "increased_monitoring", "entities_incorporated": 40},
        {"iso2": "BS", "fatf_list": None, "entities_incorporated": OFFSHORE_CENTRE_MIN_ENTITIES},
        {"iso2": "SG", "fatf_list": None, "entities_incorporated": 781},
        {"iso2": "NO", "fatf_list": None, "entities_incorporated": None},
    ]
}


def test_call_for_action_is_high_and_grey_list_or_an_offshore_centre_is_medium() -> None:
    assert jurisdiction_tiers(PAYLOAD) == {"MM": "high", "VN": "medium", "BS": "medium"}


def test_unlisted_countries_are_absent_not_labelled_safe() -> None:
    tiers = jurisdiction_tiers(PAYLOAD)
    assert "SG" not in tiers and "NO" not in tiers


def test_an_empty_payload_gives_no_tiers() -> None:
    assert jurisdiction_tiers({"countries": []}) == {}
