"""Regression tests pinning down known dataset-quality issues in
`data/convfinqa_dataset.json`.

These are *failing-by-design* in the upstream sense: each asserts that a
specific data-quality issue *still exists* in the shipped JSON. When the
dataset is re-shipped clean, these tests flip red and force the report's
limitations section to be updated.

We don't own the cleaner — the JSON is provided as-is. These tests document
the state of the data we ran v0 against, so the report's claims about
unrecoverable failures can be machine-checked rather than vibes-cited.
"""

import pytest

from src.repository.convfinqa import JsonDatasetRepository
from src.settings import Settings


@pytest.fixture(scope="module")
def train_records():
    return {r.id: r for r in JsonDatasetRepository(Settings()).load_split("train")}


def _document_haystack(record) -> str:
    """Concatenate every place a number could legitimately appear: pre/post
    narrative + every table cell rendered as its raw value. Used to test
    'is X anywhere in this document?'.
    """
    table_text = " ".join(
        str(cell) for column in record.doc.table.values() for cell in column.values()
    )
    return f"{record.doc.pre_text} {record.doc.post_text} {table_text}"


def test_awk_dsl_constants_missing_from_document(train_records):
    """AWK/2013: gold turn_program uses literal constants `3734` and `2059`
    for "decreases in 2011 / 2012", but neither value exists anywhere in the
    document. The cleaning step lost the per-year breakdown rows. These
    turns are unrecoverable from the model side — gold cannot be derived
    from what the model sees.
    """
    record = train_records["Double_AWK/2013/page_123.pdf"]
    haystack = _document_haystack(record)

    assert "3734" not in haystack, (
        "Dataset state changed: '3734' is now in the AWK/2013 document. "
        "Update REPORT.md limitations section — this turn may now be recoverable."
    )
    assert "2059" not in haystack
    assert record.dialogue.turn_program[1] == "3734"
    assert record.dialogue.turn_program[2] == "2059"


def test_stt_gold_lives_in_post_text_not_table(train_records):
    """STT/2008: the question "what was the total conduit asset in 2008?"
    has gold `23.59`, which appears in `post_text` referring to *liquidity
    asset purchase agreements* — not the table's `total conduit assets`
    row, which has `23.89`. Distinct financial concepts; the question
    phrasing is ambiguous between them. Recoverable in principle by a
    model that picks the post_text concept; not a cleaning artefact.
    """
    record = train_records["Double_STT/2008/page_116.pdf"]

    assert record.doc.table["2008 amount (1)"]["total conduit assets"] == 23.89
    assert record.doc.table["2008 amount (2)"]["total conduit assets"] == 28.76

    assert "23.59" in record.doc.post_text
    assert "28.37" in record.doc.post_text

    assert record.dialogue.executed_answers[0] == 23.59
    assert record.dialogue.executed_answers[1] == 28.37


def test_ipg_row_labels_swapped_vs_dsl(train_records):
    """IPG/2018: turn_program literal `3824` is the gold for the t0
    question about "november", and `1750` is the gold for the t1 question
    about "october". The cleaned table maps `3824` to october and `1750`
    to november — opposite of the gold/DSL pairing. Either the cleaner
    swapped row labels or the upstream FinQA gold was mislabelled; cannot
    confirm without the upstream source.
    """
    record = train_records["Single_IPG/2018/page_26.pdf-2"]

    purchased = record.doc.table["total number ofshares ( or units ) purchased1"]
    assert purchased["october 1 - 31"] == 3824.0
    assert purchased["november 1 - 30"] == 1750.0

    assert (
        record.dialogue.conv_questions[0]
        .lower()
        .startswith("what was the total number of shares purchased in november")
    )
    assert record.dialogue.executed_answers[0] == 3824.0
    assert record.dialogue.turn_program[0] == "3824"

    assert (
        record.dialogue.conv_questions[1]
        .lower()
        .startswith("and what was it in october")
    )
    assert record.dialogue.executed_answers[1] == 1750.0
    assert record.dialogue.turn_program[1] == "1750"
