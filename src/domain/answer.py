from pydantic import BaseModel, Field


class PredictedAnswer(BaseModel):
    reasoning: str = Field(description="Model's chain-of-thought for the answer.")
    answer: str = Field(
        description="Answer string as emitted by the model, e.g. '0.14136', '25587.0', 'yes'. "
        "Never pre-parsed; the metric layer parses at compare time."
    )
    unit: str = Field(
        description="Model's declared unit hint: one of 'raw', 'percent', 'ratio', 'none'."
    )
