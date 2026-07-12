from pathlib import Path

import pytest

from app.services.extraction import TextExtractionError, extract_text


class FakeOcrEngine:
    def __init__(self, text: str = "OCR text") -> None:
        self.text = text
        self.paths: list[Path] = []

    def extract_image_text(self, image_path: Path) -> str:
        self.paths.append(image_path)
        return self.text


def test_image_extraction_requires_ocr_engine(tmp_path) -> None:
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"not-a-real-image")

    with pytest.raises(TextExtractionError, match="requires OCR_PROVIDER"):
        extract_text(image_path, content_type="image/png")


def test_image_extraction_uses_ocr_engine(tmp_path) -> None:
    image_path = tmp_path / "scan.png"
    image_path.write_bytes(b"not-a-real-image")
    ocr_engine = FakeOcrEngine("Invoice total")

    text = extract_text(image_path, content_type="image/png", ocr_engine=ocr_engine)

    assert text == "Invoice total"
    assert ocr_engine.paths == [image_path]


def test_pdf_without_text_reports_ocr_requirement_when_ocr_disabled(tmp_path) -> None:
    from pypdf import PdfWriter

    pdf_path = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with pdf_path.open("wb") as file:
        writer.write(file)

    with pytest.raises(TextExtractionError, match="Scanned PDFs require OCR_PROVIDER"):
        extract_text(pdf_path, content_type="application/pdf")
