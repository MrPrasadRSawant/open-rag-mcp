from fastapi import APIRouter

from app.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
    VectorStoreDependency,
)
from app.schemas.documents import SearchRequest, SearchResponse
from app.services.documents import search_documents

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    session: SessionDependency,
    settings: SettingsDependency,
    vector_store: VectorStoreDependency,
    current_user: CurrentUserDependency,
) -> SearchResponse:
    return SearchResponse(
        query=payload.query,
        results=search_documents(
            session=session,
            vector_store=vector_store,
            settings=settings,
            query=payload.query,
            group_ids=payload.group_ids,
            limit=payload.limit,
            owner_id=current_user.id,
        ),
    )
