"""Single-turn answerer.

Phase 2 scope: one document, one question, one tool call. `answer_single`
returns an `AnswerCall` carrying both the parsed answer and the full audit
trail (system prompt, messages, raw response) so the orchestrator can write
self-contained transcripts without reaching into private state.
"""

from typing import Any

from pydantic import BaseModel

from src.domain import Document, PredictedAnswer
from src.prompts.system import build_system_prompt
from src.services.llm_client import LLMClient
from src.tools.submit_answer import SubmitAnswer


class AnswerCall(BaseModel):
    """One LLM call: parsed answer + everything needed to replay or audit it."""

    predicted: PredictedAnswer
    system_prompt: str
    messages: list[dict[str, Any]]
    raw_response: dict[str, Any]


class Answerer:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def answer_single(self, document: Document, question: str) -> AnswerCall:
        system = build_system_prompt(document)
        messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

        parsed, raw = self._llm.predict_with_tool(
            system=system,
            messages=messages,
            tool_model=SubmitAnswer,
        )
        predicted = PredictedAnswer.model_validate(parsed.model_dump())

        return AnswerCall(
            predicted=predicted,
            system_prompt=system,
            messages=messages,
            raw_response=raw,
        )
