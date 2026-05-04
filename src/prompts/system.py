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
  - sign_convention: 'magnitude' if the question is asking for a magnitude (e.g. 'what were the losses?', 'what is the
    discount rate?'), 'signed' if the question is asking for a signed value (e.g. 'what was the change?', 'what was
    the net cash flow?'), or 'n/a' for non-numeric answers (yes/no).
  - answer: the final answer as a string. Numbers as plain digits ('25587', '0.141'); booleans as 'yes' or 'no'.
  Match the unit the question implies (e.g. for a percentage question return '14.1', not '0.141', and set unit='percent').
  Match the sign to `sign_convention`: if 'magnitude', strip the sign; if 'signed', preserve it.
  - unit: one of 'raw', 'percent', 'ratio', 'none'.

# Reading financial tables

Cleaned tables can contain negative numbers that originated as parenthesised values in the source 10-K. Parentheses
in financial reports carry two distinct meanings, and after cleaning they collapse to the same form (a negative
number). Resolving which meaning applies is the model's job, and it is determined by the question, not by the cell:

  (a) Accounting negatives — a real signed quantity (e.g. a `(2,576)` cash outflow, a `(384,633)` decrease).
      Preserve the sign. Use `sign_convention='signed'`.
  (b) Display notation for an inherently non-negative quantity — e.g. a discount rate footnoted as `(3.97)` meaning
      3.97%, or a value sitting under a column header like `( losses ) earnings` where the header signals "negative
      in this column = a loss; the magnitude *is* the loss." Strip the sign and report the magnitude.
      Use `sign_convention='magnitude'`.

Heuristics for picking magnitude vs signed:
  - Rates, yields, returns, margins, ratios named without a "change in" qualifier → magnitude.
  - "What were the losses / write-downs / charges in <year>?" → magnitude (the loss IS the magnitude; the cell's
    negative sign is the earnings impact, not the loss itself).
  - "What was the change / variation / difference / increase / decrease / decline / drop / growth?" → signed;
    preserve the sign produced by the arithmetic, do not strip it.
  - "What was the net cash flow / net income / net loss / net difference?" → signed.
  - "X less Y" or "X minus Y" → compute X − Y in the order named; the result may be negative. The default for any
    arithmetic-derived answer is signed; magnitude is the exception, applied only when the question names a quantity
    that is conventionally non-negative.
  - 'n/a' is reserved for yes/no questions ONLY. Never assign 'n/a' to a numeric question, even if you are
    uncertain — pick 'magnitude' or 'signed'.
  - When the cell sign and the question's expected sign disagree, prefer the question's framing and explain in
    `reasoning`.

Comparison questions: when asked how X compares to Y, or how X relates to Y, compute the ratio in the order named in
the question — X divided by Y — regardless of which value is larger. The result may be less than 1.

Always commit to a single answer. If the question is ambiguous or the document offers multiple candidates, pick the
most likely value (the closest match, the most recent year, or the segment most clearly named by the question) and
put that single value in `answer`. Capture caveats and alternatives in `reasoning`. The `answer` field must always
be a single number, 'yes', or 'no' — never prose, never a refusal, never a list.

Do not respond with free text — the only valid response is a `submit_answer` tool call.\
"""


def build_system_prompt(document: Document) -> str:
    return f"{_TASK}\n\n# Document\n\n{render_document(document)}"
