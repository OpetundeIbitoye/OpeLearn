"""Docling PDF parsing in document reading order, retaining whole tables."""

import csv
import io
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    SectionHeaderItem,
    TableItem,
    TextItem,
)

from app.corpus.schemas import Block
from app.kernel.config import settings


def serialize_table(table: TableItem, document: DoclingDocument) -> str:
    """Keep every cell and span without Markdown padding or duplicated merged cells.

    TSV quoting preserves tabs, newlines, and numeric spelling inside cells.
    Span coordinates are one-based and refer to the complete rectangular grid.
    """
    rows = [[""] * table.data.num_cols for _ in range(table.data.num_rows)]
    spans: list[str] = []
    for cell in table.data.table_cells:
        row, column = cell.start_row_offset_idx, cell.start_col_offset_idx
        rows[row][column] = cell._get_text(doc=document)
        if cell.row_span > 1 or cell.col_span > 1:
            spans.append(f"{row + 1},{column + 1},{cell.row_span},{cell.col_span}")
    buffer = io.StringIO()
    csv.writer(buffer, delimiter="\t", lineterminator="\n").writerows(rows)
    text = buffer.getvalue().removesuffix("\n")
    caption = table.caption_text(document)
    if caption:
        text = caption + "\n\n" + text
    if spans:
        text += "\nMerged cells [row,column,height,width] (1-based): " + ";".join(spans)
    return text


def parse_pdf(path: Path) -> list[Block]:
    options = PdfPipelineOptions(
        artifacts_path=Path(settings.model_directory) / "docling",
        do_ocr=False,
        do_table_structure=True,
    )
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    converted = converter.convert(path, raises_on_error=True)
    if converted.status.value != "success":
        raise ValueError(f"Incomplete PDF conversion: {converted.status}")
    document = converted.document
    heading = "Document"
    blocks: list[Block] = []
    for item, _ in document.iterate_items():
        if (
            isinstance(item, SectionHeaderItem)
            or getattr(item, "label", None) == DocItemLabel.TITLE
        ):
            heading = item.text
        elif isinstance(item, (TextItem, TableItem)):
            if item.label in {DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER}:
                continue
            if not item.prov:
                raise ValueError("Parsed content has no page provenance")
            is_table = isinstance(item, TableItem)
            text = serialize_table(item, document) if is_table else item.text
            blocks.append(
                Block(
                    text=text,
                    kind="table" if is_table else "text",
                    section_heading=heading,
                    page_number=item.prov[0].page_no,
                )
            )
    if not blocks:
        raise ValueError("PDF contains no extractable text or tables")
    return blocks
