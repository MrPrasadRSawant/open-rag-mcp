from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
    VectorStoreDependency,
)
from app.schemas.documents import (
    DocumentGroupCreate,
    DocumentGroupDeleteRead,
    DocumentGroupRead,
    DocumentGroupUpdate,
)
from app.services.documents import (
    create_document_group,
    delete_document_group,
    get_document_group,
    list_document_groups,
    update_document_group,
)

router = APIRouter(prefix="/document-groups", tags=["document-groups"])


@router.post(
    "",
    response_model=DocumentGroupRead,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    payload: DocumentGroupCreate,
    session: SessionDependency,
    current_user: CurrentUserDependency,
    settings: SettingsDependency,
) -> DocumentGroupRead:
    try:
        return create_document_group(
            session,
            name=payload.name,
            description=payload.description,
            owner_id=current_user.id,
            llm_config_id=payload.llm_config_id,
            default_embedding_model=settings.embedding_model_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("", response_model=list[DocumentGroupRead])
def list_groups(
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> list[DocumentGroupRead]:
    return list_document_groups(session, owner_id=current_user.id)


@router.get("/{group_id}", response_model=DocumentGroupRead)
def get_group(
    group_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> DocumentGroupRead:
    group = get_document_group(session, group_id=group_id, owner_id=current_user.id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document group not found",
        )

    return group


@router.patch("/{group_id}", response_model=DocumentGroupRead)
def update_group(
    group_id: str,
    payload: DocumentGroupUpdate,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> DocumentGroupRead:
    group = update_document_group(
        session,
        group_id=group_id,
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document group not found",
        )
    return group


@router.delete("/{group_id}", response_model=DocumentGroupDeleteRead)
def delete_group(
    group_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
    vector_store: VectorStoreDependency,
) -> DocumentGroupDeleteRead:
    deleted = delete_document_group(
        session,
        vector_store=vector_store,
        group_id=group_id,
        owner_id=current_user.id,
    )
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document group not found",
        )
    return DocumentGroupDeleteRead(**deleted)
