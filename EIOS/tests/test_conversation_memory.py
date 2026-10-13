from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from eios.conversation.memory import ConversationMemoryManager
from eios.conversation.models import EvidenceItem


def test_compact_context_under_limit():
    manager = ConversationMemoryManager(max_tokens=4000)
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!"),
    ]
    compacted = manager.compact_context(messages)
    assert len(compacted) == 3
    assert compacted[0].content == "You are a helpful assistant."


def test_compact_context_exceeds_limit():
    manager = ConversationMemoryManager(max_tokens=100)  # Small limit
    messages = [SystemMessage(content="System prompt. " * 5)]
    # Add a lot of messages, each about ~10 tokens (40 chars)
    for i in range(20):
        messages.append(HumanMessage(content=f"This is a relatively long message number {i} " * 2))

    compacted = manager.compact_context(messages)

    # Should always preserve SystemMessage
    assert isinstance(compacted[0], SystemMessage)

    # Count approx tokens
    total_chars = sum(len(str(m.content)) for m in compacted)
    approx_tokens = total_chars // 4

    assert approx_tokens <= 120  # Give a small buffer
    # It must have pruned some messages
    assert len(compacted) < 21
    # Last message should be the most recent one
    assert "number 19" in str(compacted[-1].content)


def test_resolve_pronominal_entities():
    manager = ConversationMemoryManager()

    # Test 'his' -> '<Client>'s'
    anchors = {"client": "John Doe"}
    query = "What is his risk score?"
    resolved = manager.resolve_pronominal_entities(query, anchors)
    assert resolved == "What is John Doe's risk score?"

    # Test 'he' -> '<Client>'
    query2 = "Is he exposed to fraud?"
    resolved2 = manager.resolve_pronominal_entities(query2, anchors)
    assert resolved2 == "Is John Doe exposed to fraud?"

    # Test case insensitivity and boundaries
    query3 = "Does He know about His account?"
    resolved3 = manager.resolve_pronominal_entities(query3, anchors)
    assert resolved3 == "Does John Doe know about John Doe's account?"

    # Test unrelated query
    query4 = "Show me the dashboard."
    resolved4 = manager.resolve_pronominal_entities(query4, anchors)
    assert resolved4 == "Show me the dashboard."

    # Test no anchors
    query5 = "What is his risk score?"
    resolved5 = manager.resolve_pronominal_entities(query5, {})
    assert resolved5 == "What is his risk score?"


def test_merge_evidence():
    manager = ConversationMemoryManager()
    existing = [
        EvidenceItem(
            tool_name="tool_a",
            metric_name="metric_1",
            value=100,
            as_of="2026-10-01",
            definition_version="v1",
        ),
    ]
    new_items = [
        EvidenceItem(
            tool_name="tool_b",
            metric_name="metric_2",
            value=200,
            as_of="2026-10-01",
            definition_version="v1",
        ),
        EvidenceItem(
            tool_name="tool_a",
            metric_name="metric_1",
            value=150,
            as_of="2026-10-02",
            definition_version="v1",
        ),  # Duplicate key
    ]

    merged = manager.merge_evidence(existing, new_items)
    assert len(merged) == 2
    # The duplicate should be ignored (or updated, but our spec said "without duplicating")
    assert merged[0].tool_name == "tool_a"
    assert merged[1].tool_name == "tool_b"
