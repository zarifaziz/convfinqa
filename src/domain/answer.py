"""Domain model for one model-emitted answer.

Distinct from `SubmitAnswer` (the tool schema in `src/tools/`): that one is the
wire format the LLM fills in; this is the runtime container the rest of the
codebase passes around. Keeping them separate stops tool-schema concerns
(JSON Schema enums, field descriptions, anthropic-flavoured types) from
leaking into the domain layer.
"""

from pydantic import BaseModel, Field


class PredictedAnswer(BaseModel):
    reasoning: str = Field(description="Model's chain-of-thought for the answer.")
    calculation: str = Field(
        description="Arithmetic expression the model derived (audit-only; not executed)."
    )
    answer: str = Field(
        description="Raw answer string as emitted, e.g. '14.1%', '$25,587', '206588', 'yes'. "
        "Never pre-parsed; the metric layer parses at compare time."
    )
    unit: str = Field(
        description="Model's declared unit hint: one of 'raw', 'percent', 'ratio', 'none'."
    )
