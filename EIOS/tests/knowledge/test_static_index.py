from eios.knowledge.static_index import StaticIndex
from eios.ontology.omcp.port.contracts import DataOrigin
from tests.knowledge.passages import ALL, FILING, RED_FLAGS


def test_it_ranks_by_shared_words_and_never_claims_the_real_corpus() -> None:
    index = StaticIndex(ALL)
    assert index.origin is DataOrigin.FIXTURE
    assert index.search("when must a suspicious report be filed", None, 3)[0] == FILING


def test_it_filters_by_jurisdiction() -> None:
    assert StaticIndex(ALL).search("red flag virtual assets wallets", "MT", 5) == []
    assert StaticIndex(ALL).search("red flag virtual assets wallets", "LB", 5) == [RED_FLAGS]


def test_a_question_with_no_overlap_returns_nothing_not_the_nearest_text() -> None:
    assert StaticIndex(ALL).search("quarterly revenue forecast", None, 5) == []
