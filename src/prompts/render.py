"""Render a Document into the markdown blob the model sees."""

from src.domain import Document


def render_table(table: dict[str, dict[str, float | str | int]]) -> str:
    """Render the nested-dict table as a markdown table; missing cells render as empty strings."""
    headers = list(table.keys())
    first_col = next(iter(table.values()))
    row_labels = list(first_col.keys())

    rows = [
        [label] + [str(table[col].get(label, "")) for col in headers]
        for label in row_labels
    ]
    header_row = ["", *headers]
    all_rows = [header_row, *rows]

    widths = [max(len(r[i]) for r in all_rows) for i in range(len(header_row))]
    # Row-label column gets +2 padding so the empty header doesn't visually crowd
    # the first row label.
    widths[0] += 2

    def fmt_row(cells: list[str]) -> str:
        return "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells)) + " |"

    lines = [
        fmt_row(header_row),
        fmt_row(["-" * w for w in widths]),
        *(fmt_row(r) for r in rows),
    ]
    return "\n".join(lines)


def render_document(doc: Document) -> str:
    return f"""\
## Document context (before table)
{doc.pre_text}

## Table
{render_table(doc.table)}

## Document context (after table)
{doc.post_text}"""
