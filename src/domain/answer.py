from pydantic import BaseModel, Field


class PredictedAnswer(BaseModel):
    reasoning: str = Field(description="Model's chain-of-thought for the answer.")
    calculation: str = Field(
        description="Arithmetic expression the model derived (audit-only; not executed)."
    )
    sign_convention: str = Field(
        description="Model's declared sign-convention choice: one of 'magnitude', 'signed', 'n/a'. "
        "Persisted into predictions.jsonl so error analysis can slice by it."
    )
    answer: str = Field(
        description="Raw answer string as emitted, e.g. '14.1%', '$25,587', '206588', 'yes'. "
        "Never pre-parsed; the metric layer parses at compare time."
    )
    unit: str = Field(
        description="Model's declared unit hint: one of 'raw', 'percent', 'ratio', 'none'."
    )
