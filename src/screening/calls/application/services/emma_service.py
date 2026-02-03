from dataclasses import dataclass
from typing import AsyncIterator, Optional

from src.screening.calls.domain.entities import TranscriptSegment


@dataclass
class EmmaTurn:
    text: str
    control: Optional[str] = None


class EmmaService:
    def __init__(self, llm_generate: callable = None) -> None:
        self._llm_generate = llm_generate or _stub_llm

    async def greeting(self, role_context: str) -> str:
        return "Hello! Thanks for joining. I'm Emma. I'll ask you a few questions about your experience. Ready when you are."

    async def next_question(
        self,
        question_index: int,
        prepared_questions: list,
        role_context: str,
    ) -> Optional[str]:
        if question_index >= len(prepared_questions):
            return None
        return prepared_questions[question_index]

    async def answer_role_question(
        self, question: str, role_context: str
    ) -> str:
        if self._llm_generate:
            return await self._llm_generate(
                system=f"Answer only using this role context. Do not invent information.\n\n{role_context}",
                user=question,
            )
        return f"Based on the role: {role_context[:200]}..."

    async def goodbye(self) -> str:
        return "That's all from my side. Thanks for your time. Goodbye!"


async def _stub_llm(system: str = "", user: str = "") -> str:
    return "Here's what I can tell you based on the role description."
