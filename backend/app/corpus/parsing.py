"""Docling PDF parsing in document reading order, retaining whole tables."""

from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DocItemLabel, SectionHeaderItem, TableItem, TextItem

from app.corpus.schemas import Block
from app.kernel.config import settings


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
            text = item.export_to_markdown(doc=document) if is_table else item.text
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
