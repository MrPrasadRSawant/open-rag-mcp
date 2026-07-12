from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import (
    CurrentUserDependency,
    SessionDependency,
    SettingsDependency,
    VectorStoreDependency,
)
from app.schemas.documents import DocumentCreate, DocumentDeleteRead, DocumentRead, DocumentUpdate
from app.services.documents import (
    create_queued_text_document,
    create_queued_upload_document,
    delete_document,
    document_with_chunk_count,
    get_document_group,
    list_documents,
    update_document,
)
from app.services.jobs import process_job
from app.services.uploads import UploadTooLargeError, save_upload_file

router = APIRouter(prefix="/document-groups/{group_id}/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_document(
    group_id: str,
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> DocumentRead:
    try:
        document, job = create_queued_text_document(
            session,
            group_id=group_id,
            payload=payload,
            owner_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    background_tasks.add_task(process_job, job.id, settings)
    return document_with_chunk_count(document, processing_job_id=job.id)


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    group_id: str,
    background_tasks: BackgroundTasks,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> DocumentRead:
    try:
        stored_upload = await save_upload_file(
            file,
            upload_directory=settings.resolved_upload_directory,
            max_size_bytes=settings.max_upload_size_bytes,
        )
        document, job = create_queued_upload_document(
            session,
            group_id=group_id,
            owner_id=current_user.id,
            title=title or stored_upload.filename,
            source_name=stored_upload.filename,
            content_type=stored_upload.content_type,
            storage_path=str(stored_upload.path),
            file_size_bytes=stored_upload.size_bytes,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    background_tasks.add_task(process_job, job.id, settings)
    return document_with_chunk_count(document, processing_job_id=job.id)


@router.get("", response_model=list[DocumentRead])
def list_group_documents(
    group_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> list[DocumentRead]:
    group = get_document_group(session, group_id=group_id, owner_id=current_user.id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document group not found",
        )

    return [
        document_with_chunk_count(document)
        for document in list_documents(session, group_id=group_id, owner_id=current_user.id)
    ]


@router.patch("/{document_id}", response_model=DocumentRead)
def update_group_document(
    group_id: str,
    document_id: str,
    payload: DocumentUpdate,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> DocumentRead:
    document = update_document(
        session,
        document_id=document_id,
        group_id=group_id,
        owner_id=current_user.id,
        title=payload.title,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document_with_chunk_count(document)


@router.delete("/{document_id}", response_model=DocumentDeleteRead)
def delete_group_document(
    group_id: str,
    document_id: str,
    session: SessionDependency,
    vector_store: VectorStoreDependency,
    current_user: CurrentUserDependency,
) -> DocumentDeleteRead:
    deleted = delete_document(
        session,
        vector_store=vector_store,
        document_id=document_id,
        group_id=group_id,
        owner_id=current_user.id,
    )
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return DocumentDeleteRead(**deleted)
