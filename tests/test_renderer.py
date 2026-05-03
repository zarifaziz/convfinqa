"""Snapshot tests for the document renderer.

Two layers:
  1. `render_table` snapshot on a tiny synthetic table — pins the exact
     markdown layout the model will see.
  2. `render_document` framing snapshot on a real record — pins the
     pre-text / table / post-text wrapping (cleaning policy is "do nothing",
     so cells flow through unchanged).
"""

from src.domain import Document
from src.prompts.render import render_document, render_table


def test_render_table_simple_two_column() -> None:
    """Outer keys become column headers; inner keys become row labels."""
    table: dict[str, dict[str, float | str | int]] = {
        "2009": {"net income": 103102.0, "revenue": 200.0},
        "2008": {"net income": 104222.0, "revenue": 180.0},
    }

    expected = (
        "|              | 2009     | 2008     |\n"
        "| ------------ | -------- | -------- |\n"
        "| net income   | 103102.0 | 104222.0 |\n"
        "| revenue      | 200.0    | 180.0    |"
    )
    assert render_table(table) == expected


def test_render_table_passes_non_numeric_cells_through() -> None:
    """`'-'`, `'( in thousands )'`, `'nm'` etc. flow through unchanged."""
    table: dict[str, dict[str, float | str | int]] = {
        "2009": {"unit": "( in thousands )", "net income": 103102.0, "missing": "-"},
        "2008": {"unit": "( in thousands )", "net income": "nm", "missing": ""},
    }

    rendered = render_table(table)
    assert "( in thousands )" in rendered
    assert "nm" in rendered
    assert "-" in rendered


def test_render_table_handles_duplicate_column_suffixes() -> None:
    """Duplicate column headers carry `(1)`/`(2)` suffixes — render as-is."""
    table: dict[str, dict[str, float | str | int]] = {
        "net sales 2006 (1)": {"industrial": 3236.0, "glass": 2229.0},
        "net sales 2005": {"industrial": 2921.0, "glass": 2214.0},
        "net sales 2006 (2)": {"industrial": 349.0, "glass": 148.0},
    }

    rendered = render_table(table)
    assert "net sales 2006 (1)" in rendered
    assert "net sales 2006 (2)" in rendered
    assert "net sales 2005" in rendered


def test_render_document_frames_table_with_pre_and_post_sections() -> None:
    """Three labelled markdown sections, no XML tags."""
    doc = Document(
        pre_text="narrative before",
        post_text="narrative after",
        table={"2009": {"x": 1.0}},
    )

    rendered = render_document(doc)
    table_md = render_table(doc.table)

    expected = (
        "## Document context (before table)\n"
        "narrative before\n\n"
        "## Table\n"
        f"{table_md}\n\n"
        "## Document context (after table)\n"
        "narrative after"
    )
    assert rendered == expected
