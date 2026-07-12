from pathlib import Path
from typing import Protocol

from app.core.config import OcrProvider, Settings


class OcrEngine(Protocol):
    def extract_image_text(self, image_path: Path) -> str:
        raise NotImplementedError


class PaddleOcrEngine:
    def __init__(self, *, language: str) -> None:
        self.language = language
        self._engine = None

    def extract_image_text(self, image_path: Path) -> str:
        engine = self._get_engine()
        result = engine.ocr(str(image_path), cls=True)
        lines = _flatten_paddle_result(result)
        return "\n".join(lines).strip()

    def _get_engine(self):
        if self._engine is not None:
            return self._engine

        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError(
                "PaddleOCR is not installed. Install OCR dependencies with "
                "`pip install -e backend[ocr]` or set OCR_PROVIDER=disabled."
            ) from exc

        self._engine = PaddleOCR(use_angle_cls=True, lang=self.language)
        return self._engine


def get_ocr_engine(settings: Settings) -> OcrEngine | None:
    if settings.ocr_provider == OcrProvider.disabled:
        return None
    if settings.ocr_provider == OcrProvider.paddle:
        return PaddleOcrEngine(language=settings.ocr_language)

    raise ValueError(f"Unsupported OCR provider: {settings.ocr_provider}")


def _flatten_paddle_result(result) -> list[str]:
    lines: list[str] = []
    if not result:
        return lines

    for page in result:
        if not page:
            continue
        for item in page:
            if not item or len(item) < 2:
                continue
            text_candidate = item[1]
            if isinstance(text_candidate, (list, tuple)) and text_candidate:
                text = text_candidate[0]
            else:
                text = text_candidate
            if isinstance(text, str) and text.strip():
                lines.append(text.strip())

    return lines
