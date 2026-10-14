"""Real oversized-table regression; verify every cell, span, and the strict ceiling."""

import csv
import io
import json
from pathlib import Path

from docling_core.types.doc import DocItemLabel, DoclingDocument, TableData

from app.corpus.chunking import chunk_blocks
from app.corpus.embedding import get_model
from app.corpus.parsing import serialize_table
from app.corpus.schemas import Block


def test_complete_table_fits_without_losing_cells_or_spans() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures/attention-table-3.json").read_text())
    document = DoclingDocument(name="attention-table-3")
    table = document.add_table(data=TableData.model_validate(fixture["data"]))
    caption = document.add_text(label=DocItemLabel.CAPTION, text=fixture["caption"])
    table.captions.append(caption.get_ref())
    text = serialize_table(table, document)
    assert text.startswith(fixture["caption"] + "\n\n")
    grid_text, spans_text = text.removeprefix(fixture["caption"] + "\n\n").split(
        "\nMerged cells [row,column,height,width] (1-based): "
    )
    rows = list(csv.reader(io.StringIO(grid_text), delimiter="\t"))
    assert len(rows) == table.data.num_rows
    assert all(len(row) == table.data.num_cols for row in rows)
    expected_spans = []
    for cell in table.data.table_cells:
        assert rows[cell.start_row_offset_idx][cell.start_col_offset_idx] == cell.text
        if cell.row_span > 1 or cell.col_span > 1:
            expected_spans.append(
                f"{cell.start_row_offset_idx + 1},{cell.start_col_offset_idx + 1},"
                f"{cell.row_span},{cell.col_span}"
            )
    assert spans_text.split(";") == expected_spans
    assert text.count("positional embedding instead of sinusoids") == 1
    chunks = chunk_blocks(
        [Block(text=text, kind="table", section_heading="Results", page_number=fixture["page"])],
        get_model().tokenizer,
    )
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].token_count <= 600
    assert chunks[0].page_number == 9
