import tempfile
from pathlib import Path

from app.services.ocr import OcrEngine


class UnsupportedDocumentTypeError(ValueError):
    pass


class TextExtractionError(ValueError):
    pass


def extract_text(
    path: Path,
    *,
    content_type: str,
    ocr_engine: OcrEngine | None = None,
    ocr_pdf_dpi: int = 200,
) -> str:
    if content_type.startswith("text/"):
        return _extract_text_file(path)
    if content_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return _extract_pdf(path, ocr_engine=ocr_engine, ocr_pdf_dpi=ocr_pdf_dpi)
    if content_type.startswith("image/"):
        return _extract_image(path, ocr_engine=ocr_engine)

    raise UnsupportedDocumentTypeError(
        "Only text files, PDFs, and image files are supported by this endpoint"
    )


def _extract_text_file(path: Path) -> str:
    content = path.read_bytes()
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _extract_pdf(
    path: Path,
    *,
    ocr_engine: OcrEngine | None,
    ocr_pdf_dpi: int,
) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise TextExtractionError("PDF extraction dependency is not installed") from exc

    try:
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise TextExtractionError(f"Could not extract text from PDF: {exc}") from exc

    if not text:
        return _extract_pdf_with_ocr(path, ocr_engine=ocr_engine, ocr_pdf_dpi=ocr_pdf_dpi)

    return text


def _extract_image(path: Path, *, ocr_engine: OcrEngine | None) -> str:
    if ocr_engine is None:
        raise TextExtractionError("Image text extraction requires OCR_PROVIDER=paddle")

    text = ocr_engine.extract_image_text(path)
    if not text:
        raise TextExtractionError("No text could be extracted from this image")

    return text


def _extract_pdf_with_ocr(
    path: Path,
    *,
    ocr_engine: OcrEngine | None,
    ocr_pdf_dpi: int,
) -> str:
    if ocr_engine is None:
        raise TextExtractionError(
            "No text could be extracted from this PDF. Scanned PDFs require OCR_PROVIDER=paddle."
        )

    try:
        import fitz
    except ImportError as exc:
        raise TextExtractionError(
            "Scanned PDF OCR requires PyMuPDF. Install OCR dependencies with "
            "`pip install -e backend[ocr]`."
        ) from exc

    extracted_pages: list[str] = []
    scale = ocr_pdf_dpi / 72
    matrix = fitz.Matrix(scale, scale)
    with tempfile.TemporaryDirectory() as temp_dir:
        document = fitz.open(path)
        try:
            for page_index, page in enumerate(document):
                image_path = Path(temp_dir) / f"page-{page_index + 1}.png"
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                pixmap.save(image_path)
                page_text = ocr_engine.extract_image_text(image_path)
                if page_text:
                    extracted_pages.append(page_text)
        finally:
            document.close()

    text = "\n\n".join(extracted_pages).strip()
    if not text:
        raise TextExtractionError("No text could be extracted from this scanned PDF")

    return text
