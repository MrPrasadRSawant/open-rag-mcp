from pydantic import BaseModel


class DocumentationPage(BaseModel):
    slug: str
    title: str
    category: str
    order: int
    content: str


class DocumentationCategory(BaseModel):
    key: str
    label: str
    pages: list[DocumentationPage]


class DocumentationCatalog(BaseModel):
    categories: list[DocumentationCategory]

