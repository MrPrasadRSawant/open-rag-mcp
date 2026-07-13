from fastapi import APIRouter

from app.api.dependencies import CurrentUserDependency
from app.schemas.documentation import DocumentationCatalog
from app.services.documentation import get_documentation_catalog

router = APIRouter(prefix="/documentation", tags=["documentation"])


@router.get("", response_model=DocumentationCatalog)
def documentation_catalog(_: CurrentUserDependency) -> DocumentationCatalog:
    return get_documentation_catalog()

