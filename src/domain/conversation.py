"""Runtime container for one record's predictions.

Pure domain data: a list of completed `Turn`s. Anthropic-shape
serialization lives in `src/services/anthropic.py` — `Conversation`
carries no provider knowledge.
"""

from pydantic import BaseModel, Field

from src.domain.answer import PredictedAnswer


class Turn(BaseModel):
    """A completed turn: the question asked, the tool_use id Anthropic
    assigned to the response, and the parsed answer it produced."""

    question: str
    tool_use_id: str
    predicted: PredictedAnswer


class Conversation(BaseModel):
    turns: list[Turn] = Field(default_factory=list)
