"""Domain models for the cleaned ConvFinQA dataset.
"""

from pydantic import BaseModel, Field


class Document(BaseModel):
    pre_text: str = Field(description="Narrative text appearing before the table on the source page.")
    post_text: str = Field(description="Narrative text appearing after the table on the source page.")
    table: dict[str, dict[str, float | str | int]] = Field(
        description="Table as a nested dict. Outer key is the column label (typically a year); "
        "inner dict maps row label to cell value. Cells may be non-numeric where cleaning could not coerce them."
    )


class Dialogue(BaseModel):
    conv_questions: list[str] = Field(
        description="Per-turn questions in the conversation (originally `dialogue_break` in the source data)."
    )
    conv_answers: list[str] = Field(
        description="Per-turn human-written answer strings (e.g. '14.1%'). Display-only; use `executed_answers` for grading."
    )
    turn_program: list[str] = Field(
        description="Per-turn DSL program from the FinQA paper (e.g. 'subtract(206588, 181001)'). "
        "Useful as eval metadata (operator count, #N back-refs, const_X usage); never feed to the model."
    )
    executed_answers: list[float | str] = Field(
        description="Per-turn gold execution result. Source of truth for execution accuracy."
    )
    qa_split: list[bool] = Field(
        description="Per-turn provenance flag for hybrid (Type II) conversations: "
        "False = decomposed from the first source FinQA question, True = from the second. "
        "Type I (simple) conversations are all False."
    )


class Features(BaseModel):
    num_dialogue_turns: int = Field(description="Length of conv_questions.")
    has_type2_question: bool = Field(
        description="True iff qa_split contains any True (i.e. the conversation is hybrid / Type II)."
    )
    has_duplicate_columns: bool = Field(
        description="True if duplicate column headers in the source table were not algorithmically resolved "
        "and instead suffixed (e.g. 'Revenue (1)', 'Revenue (2)')."
    )
    has_non_numeric_values: bool = Field(description="True if any table cell remains non-numeric after cleaning.")


class ConvFinQARecord(BaseModel):
    id: str = Field(description="Stable record id, e.g. 'Single_JKHY/2009/page_28.pdf-3'.")
    doc: Document
    dialogue: Dialogue
    features: Features
