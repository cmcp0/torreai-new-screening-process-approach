"""
Unit tests for EmmaService (Phase 2 Testing Strategy).
LLM/STT/TTS are mocked (or use built-in stub).
"""
import pytest
from unittest.mock import AsyncMock

from src.screening.calls.application.services import EmmaService


@pytest.fixture
def mock_llm():
    return AsyncMock(return_value="Mocked role answer.")


@pytest.fixture
def emma_service(mock_llm):
    return EmmaService(llm_generate=mock_llm)


@pytest.fixture
def emma_service_stub():
    return EmmaService(llm_generate=None)


@pytest.mark.asyncio
async def test_greeting_returns_fixed_message(emma_service):
    out = await emma_service.greeting("Objective: Build APIs")
    assert "Emma" in out
    assert "questions" in out or "experience" in out


@pytest.mark.asyncio
async def test_next_question_returns_prepared_questions(emma_service):
    questions = ["Q1", "Q2", "Q3"]
    q0 = await emma_service.next_question(0, questions, "context")
    assert q0 == "Q1"
    q1 = await emma_service.next_question(1, questions, "context")
    assert q1 == "Q2"
    q3 = await emma_service.next_question(3, questions, "context")
    assert q3 is None


@pytest.mark.asyncio
async def test_answer_role_question_uses_llm_when_provided(emma_service, mock_llm):
    out = await emma_service.answer_role_question("What does the role involve?", "Objective: Build APIs")
    assert out == "Mocked role answer."
    mock_llm.assert_awaited_once()
    kwargs = getattr(mock_llm.call_args, "kwargs", mock_llm.call_args[1] if len(mock_llm.call_args) > 1 else {})
    assert kwargs.get("system", "").startswith("Answer only") or "Objective" in kwargs.get("system", "")


@pytest.mark.asyncio
async def test_answer_role_question_fallback_when_no_llm(emma_service_stub):
    out = await emma_service_stub.answer_role_question("What does the role involve?", "Objective: Build APIs")
    assert "Based on the role" in out or "role" in out.lower()


@pytest.mark.asyncio
async def test_goodbye_returns_fixed_message(emma_service):
    out = await emma_service.goodbye()
    assert "goodbye" in out.lower() or "thanks" in out.lower()
