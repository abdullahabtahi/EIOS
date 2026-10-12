import pytest
from langchain_core.messages import HumanMessage
from eios.conversation.specialists.synthesis import SynthesisSpecialist
from eios.conversation.models import BlackboardState

def test_synthesis_no_counterfactual():
    spec = SynthesisSpecialist()
    state = {"messages": [HumanMessage(content="What is the net revenue?")]}
    result = spec.invoke(state)
    assert "Synthesis specialist analysis completed." in str(result["messages"][0].content)
    assert "WARNING" not in str(result["messages"][0].content)
    assert "Executing scenario" not in str(result["messages"][0].content)

def test_synthesis_counterfactual_safe():
    spec = SynthesisSpecialist()
    state = {"messages": [HumanMessage(content="What if revenue drops by 2.5 sigma?")]}
    result = spec.invoke(state)
    content = str(result["messages"][0].content)
    assert "Executing scenario" in content
    assert "WARNING" not in content

def test_synthesis_counterfactual_extrapolation_warning():
    spec = SynthesisSpecialist()
    state = {"messages": [HumanMessage(content="What if retention drops by 4.5 sigma?")]}
    result = spec.invoke(state)
    content = str(result["messages"][0].content)
    assert "WARNING: The requested shock (4.5) exceeds 3.0 sigma" in content
