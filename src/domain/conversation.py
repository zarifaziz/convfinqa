from pydantic import BaseModel, Field

from src.domain.answer import PredictedAnswer


class Turn(BaseModel):
    question: str
    tool_use_id: str
    predicted: PredictedAnswer


class Conversation(BaseModel):
    turns: list[Turn] = Field(default_factory=list)
