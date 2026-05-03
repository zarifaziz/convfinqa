"""Build the system prompt that frames each LLM call.

One pure function: take a `Document`, return the system message string. The
prompt states the task, embeds the rendered document, and reminds the model
to call the `submit_answer` tool. Tool-choice forcing handles the rest — no
need for elaborate output-format instructions.
"""

from src.domain import Document
from src.prompts.render import render_document

_TASK = """\
You are a financial-analyst assistant. Answer the user's question about the document below using only the information shown. 
Do arithmetic step-by-step. When ready, call the `submit_answer` tool exactly once with:
  - reasoning: your chain of thought
  - calculation: the arithmetic expression you used (e.g. '206588 - 181001')
  - answer: the final answer as a string. Numbers as plain digits ('25587', '0.141'); booleans as 'yes' or 'no'. 
  Match the unit the question implies (e.g. for a percentage question return '14.1', not '0.141', and set unit='percent').
  - unit: one of 'raw', 'percent', 'ratio', 'none'.

Comparison questions: when asked how X compares to Y, or how X relates to Y, compute the ratio in the order named in the
question — X divided by Y — regardless of which value is larger. The result may be less than 1.

Always commit to a single answer. If the question is ambiguous or the document offers multiple candidates, pick the most
likely value (the closest match, the most recent year, or the segment most clearly named by the question) and put that
single value in `answer`. Capture caveats and alternatives in `reasoning`. The `answer` field must always be a single
number, 'yes', or 'no' — never prose, never a refusal, never a list.

Do not respond with free text — the only valid response is a `submit_answer` tool call.\
"""


def build_system_prompt(document: Document) -> str:
    return f"{_TASK}\n\n# Document\n\n{render_document(document)}"
