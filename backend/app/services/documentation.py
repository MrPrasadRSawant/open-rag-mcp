from pathlib import Path
from threading import Lock

from app.core.config import REPOSITORY_ROOT
from app.schemas.documentation import (
    DocumentationCatalog,
    DocumentationCategory,
    DocumentationPage,
)

DOCS_ROOT = REPOSITORY_ROOT / "docs"
DOCUMENTATION_CATEGORIES = {
    "functional": ("Functional", DOCS_ROOT / "functional_docs"),
    "technical": ("Technical", DOCS_ROOT / "technical_docs"),
}

_cache: DocumentationCatalog | None = None
_lock = Lock()


def load_documentation_cache() -> DocumentationCatalog:
    global _cache
    with _lock:
        _cache = DocumentationCatalog(
            categories=[
                DocumentationCategory(
                    key=key,
                    label=label,
                    pages=_load_pages(key, directory),
                )
                for key, (label, directory) in DOCUMENTATION_CATEGORIES.items()
            ]
        )
        return _cache


def get_documentation_catalog() -> DocumentationCatalog:
    if _cache is None:
        return load_documentation_cache()
    return _cache


def _load_pages(category: str, directory: Path) -> list[DocumentationPage]:
    if not directory.exists():
        return []

    pages = [
        _read_page(category, path, index)
        for index, path in enumerate(sorted(directory.glob("*.md")), start=1)
    ]
    return sorted(pages, key=lambda page: (page.order, page.title))


def _read_page(category: str, path: Path, fallback_order: int) -> DocumentationPage:
    content = path.read_text(encoding="utf-8")
    title = _extract_title(content) or _title_from_filename(path)
    return DocumentationPage(
        slug=path.stem,
        title=title,
        category=category,
        order=_extract_order(path, fallback_order),
        content=content,
    )


def _extract_title(content: str) -> str | None:
    for line in content.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return None


def _title_from_filename(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _extract_order(path: Path, fallback_order: int) -> int:
    prefix = path.stem.split("-", 1)[0]
    if prefix.isdigit():
        return int(prefix)
    if path.stem == "index":
        return 0
    return fallback_order

