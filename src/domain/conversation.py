from typing import Any

from pydantic import BaseModel, Field

from src.domain.answer import PredictedAnswer


class Turn(BaseModel):
    question: str
    tool_use_id: str
    predicted: PredictedAnswer
    # All messages contributed by this turn's agentic loop (calculator calls +
    # submit_answer tool_use). Does NOT include the opening user question or the
    # closing tool_result ack — those are stitched in by to_messages().
    assistant_exchange: list[dict[str, Any]] = Field(default_factory=list)


class Conversation(BaseModel):
    turns: list[Turn] = Field(default_factory=list)
