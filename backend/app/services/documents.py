from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    AgentProfile,
    ApiKey,
    Document,
    DocumentChunk,
    DocumentGroup,
    LlmProviderConfig,
    ProcessingJob,
)
from app.schemas.documents import DocumentCreate, SearchResult
from app.services.embeddings import get_embedding_service_for_group
from app.services.llm_configs import get_or_create_default_embedding_config
from app.services.retrieval import RetrievalOptions, rerank_vector_results
from app.services.text_splitter import TextSplitter
from app.services.vector_store.base import VectorDocument, VectorStore


def create_document_group(
    session: Session,
    *,
    name: str,
    description: str | None = None,
    owner_id: str = "local",
    llm_config_id: str | None = None,
    default_embedding_model: str = "BAAI/bge-small-en-v1.5",
) -> DocumentGroup:
    if llm_config_id is None:
        config = get_or_create_default_embedding_config(
            session, user_id=owner_id, model_name=default_embedding_model
        )
    else:
        config = session.scalar(
            select(LlmProviderConfig).where(
                LlmProviderConfig.id == llm_config_id,
                LlmProviderConfig.user_id == owner_id,
                LlmProviderConfig.purpose == "embedding",
                LlmProviderConfig.is_active.is_(True),
            )
        )
        if config is None:
            raise ValueError("Select a valid embedding config")
    group = DocumentGroup(
        name=name,
        description=description,
        owner_id=owner_id,
        llm_config_id=config.id,
    )
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


def list_document_groups(session: Session, *, owner_id: str = "local") -> list[DocumentGroup]:
    return list(
        session.scalars(
            select(DocumentGroup)
            .where(DocumentGroup.owner_id == owner_id)
            .order_by(DocumentGroup.created_at.desc())
        )
    )


def get_document_group(
    session: Session,
    *,
    group_id: str,
    owner_id: str = "local",
) -> DocumentGroup | None:
    return session.scalar(
        select(DocumentGroup).where(
            DocumentGroup.id == group_id,
            DocumentGroup.owner_id == owner_id,
        )
    )


def update_document_group(
    session: Session,
    *,
    group_id: str,
    owner_id: str,
    name: str | None = None,
    description: str | None = None,
) -> DocumentGroup | None:
    group = get_document_group(session, group_id=group_id, owner_id=owner_id)
    if group is None:
        return None
    if name is not None:
        group.name = name
    group.description = description
    session.commit()
    session.refresh(group)
    return group


def delete_document_group(
    session: Session,
    *,
    vector_store: VectorStore,
    group_id: str,
    owner_id: str,
) -> dict[str, str | bool | int] | None:
    group = get_document_group(session, group_id=group_id, owner_id=owner_id)
    if group is None:
        return None

    document_ids = list(
        session.scalars(
            select(Document.id).where(
                Document.group_id == group_id,
                Document.owner_id == owner_id,
            )
        )
    )
    documents_deleted = len(document_ids)

    api_keys_deleted = session.query(ApiKey).filter(
        ApiKey.group_id == group_id,
        ApiKey.user_id == owner_id,
    ).delete(synchronize_session=False)
    session.query(AgentProfile).filter(
        AgentProfile.group_id == group_id,
        AgentProfile.user_id == owner_id,
    ).delete(synchronize_session=False)

    if document_ids:
        session.query(ProcessingJob).filter(
            ProcessingJob.document_id.in_(document_ids),
            ProcessingJob.owner_id == owner_id,
        ).delete(synchronize_session=False)
        session.query(DocumentChunk).filter(
            DocumentChunk.group_id == group_id,
            DocumentChunk.owner_id == owner_id,
        ).delete(synchronize_session=False)
        session.query(Document).filter(
            Document.id.in_(document_ids),
            Document.group_id == group_id,
            Document.owner_id == owner_id,
        ).delete(synchronize_session=False)

    vector_store.delete_by_metadata(
        {
            "owner_id": owner_id,
            "group_id": group_id,
        }
    )

    session.delete(group)
    session.commit()
    return {
        "id": group_id,
        "deleted": True,
        "documents_deleted": documents_deleted,
        "api_keys_deleted": api_keys_deleted,
    }


def get_document(
    session: Session,
    *,
    document_id: str,
    group_id: str,
    owner_id: str = "local",
) -> Document | None:
    return session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.group_id == group_id,
            Document.owner_id == owner_id,
        )
    )


def update_document(
    session: Session,
    *,
    document_id: str,
    group_id: str,
    owner_id: str,
    title: str | None = None,
) -> Document | None:
    document = get_document(
        session,
        document_id=document_id,
        group_id=group_id,
        owner_id=owner_id,
    )
    if document is None:
        return None
    if title is not None:
        document.title = title
    session.commit()
    session.refresh(document)
    return document


def delete_document(
    session: Session,
    *,
    vector_store: VectorStore,
    document_id: str,
    group_id: str,
    owner_id: str,
) -> dict[str, str | bool | int] | None:
    document = get_document(
        session,
        document_id=document_id,
        group_id=group_id,
        owner_id=owner_id,
    )
    if document is None:
        return None
    chunks_deleted = session.scalar(
        select(func.count())
        .select_from(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.group_id == group_id,
            DocumentChunk.owner_id == owner_id,
        )
    )
    jobs_deleted = session.scalar(
        select(func.count())
        .select_from(ProcessingJob)
        .where(
            ProcessingJob.document_id == document_id,
            ProcessingJob.owner_id == owner_id,
        )
    )
    vector_store.delete_by_metadata(
        {
            "owner_id": owner_id,
            "group_id": group_id,
            "document_id": document_id,
        }
    )
    session.query(ProcessingJob).filter(
        ProcessingJob.document_id == document_id,
        ProcessingJob.owner_id == owner_id,
    ).delete(synchronize_session=False)
    session.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id,
        DocumentChunk.group_id == group_id,
        DocumentChunk.owner_id == owner_id,
    ).delete(synchronize_session=False)
    session.delete(document)
    session.commit()
    return {
        "id": document_id,
        "group_id": group_id,
        "deleted": True,
        "chunks_deleted": chunks_deleted or 0,
        "jobs_deleted": jobs_deleted or 0,
    }


def list_documents(
    session: Session,
    *,
    group_id: str,
    owner_id: str = "local",
) -> list[Document]:
    return list(
        session.scalars(
            select(Document)
            .where(
                Document.group_id == group_id,
                Document.owner_id == owner_id,
            )
            .order_by(Document.created_at.desc())
        )
    )


def ingest_text_document(
    session: Session,
    *,
    vector_store: VectorStore,
    settings: Settings,
    group_id: str,
    payload: DocumentCreate,
    owner_id: str = "local",
) -> Document:
    group = get_document_group(session, group_id=group_id, owner_id=owner_id)
    if group is None:
        raise ValueError("document group not found")

    document = Document(
        owner_id=owner_id,
        group_id=group.id,
        title=payload.title,
        source_name=payload.source_name,
        content_type=payload.content_type,
        status="processing",
        extra_metadata=payload.metadata,
    )
    session.add(document)
    session.flush()

    index_document_text(
        session,
        vector_store=vector_store,
        settings=settings,
        document=document,
        text=payload.text,
        metadata=payload.metadata,
    )
    session.refresh(document)
    return document


def create_queued_text_document(
    session: Session,
    *,
    group_id: str,
    payload: DocumentCreate,
    owner_id: str,
) -> tuple[Document, ProcessingJob]:
    group = get_document_group(session, group_id=group_id, owner_id=owner_id)
    if group is None:
        raise ValueError("document group not found")

    document = Document(
        owner_id=owner_id,
        group_id=group.id,
        title=payload.title,
        source_name=payload.source_name,
        content_type=payload.content_type,
        status="queued",
        extra_metadata=payload.metadata,
    )
    session.add(document)
    session.flush()

    job = ProcessingJob(
        owner_id=owner_id,
        document_id=document.id,
        job_type="text_ingestion",
        status="queued",
        payload={"text": payload.text, "metadata": payload.metadata},
    )
    session.add(job)
    session.commit()
    session.refresh(document)
    session.refresh(job)
    return document, job


def create_queued_upload_document(
    session: Session,
    *,
    group_id: str,
    owner_id: str,
    title: str,
    source_name: str,
    content_type: str,
    storage_path: str,
    file_size_bytes: int,
) -> tuple[Document, ProcessingJob]:
    group = get_document_group(session, group_id=group_id, owner_id=owner_id)
    if group is None:
        raise ValueError("document group not found")

    metadata = {
        "original_filename": source_name,
        "storage_path": storage_path,
        "file_size_bytes": file_size_bytes,
    }
    document = Document(
        owner_id=owner_id,
        group_id=group.id,
        title=title,
        source_name=source_name,
        content_type=content_type,
        status="queued",
        extra_metadata=metadata,
    )
    session.add(document)
    session.flush()

    job = ProcessingJob(
        owner_id=owner_id,
        document_id=document.id,
        job_type="upload_ingestion",
        status="queued",
        payload={
            "storage_path": storage_path,
            "content_type": content_type,
            "metadata": metadata,
        },
    )
    session.add(job)
    session.commit()
    session.refresh(document)
    session.refresh(job)
    return document, job


def index_document_text(
    session: Session,
    *,
    vector_store: VectorStore,
    settings: Settings,
    document: Document,
    text: str,
    metadata: dict[str, Any],
) -> Document:
    splitter = TextSplitter(settings.chunk_size, settings.chunk_overlap)
    embedding_service = get_embedding_service_for_group(session, document.group_id, settings)
    chunks = splitter.split(text)
    if not chunks:
        raise ValueError("document text did not contain indexable content")

    document.status = "processing"
    document.error_message = None
    session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    vector_store.delete_by_metadata(
        {
            "owner_id": document.owner_id,
            "group_id": document.group_id,
            "document_id": document.id,
        }
    )
    session.flush()

    chunk_models = [
        DocumentChunk(
            owner_id=document.owner_id,
            group_id=document.group_id,
            document_id=document.id,
            chunk_index=index,
            text=chunk_text,
            token_count=len(chunk_text.split()),
        )
        for index, chunk_text in enumerate(chunks)
    ]
    session.add_all(chunk_models)
    session.flush()

    vector_documents = [
        VectorDocument(
            id=chunk.id,
            text=chunk.text,
            embedding=embedding_service.embed_document(chunk.text),
            metadata=_clean_metadata(
                {
                    "owner_id": document.owner_id,
                    "group_id": document.group_id,
                    "document_id": document.id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "title": document.title,
                    **metadata,
                }
            ),
        )
        for chunk in chunk_models
    ]

    vector_store.add_documents(vector_documents)

    document.status = "processed"
    session.commit()
    session.refresh(document)
    return document


def search_documents(
    *,
    session: Session,
    vector_store: VectorStore,
    settings: Settings,
    query: str,
    group_ids: list[str] | None = None,
    limit: int = 5,
    owner_id: str = "local",
    candidate_limit: int | None = None,
    rerank: bool | None = None,
    lexical_weight: float | None = None,
    diversity: bool | None = None,
    diversity_lambda: float | None = None,
    min_score: float | None = None,
) -> list[SearchResult]:
    retrieval_options = RetrievalOptions(
        limit=limit,
        candidate_limit=candidate_limit or settings.retrieval_candidate_limit,
        rerank=settings.retrieval_rerank_enabled if rerank is None else rerank,
        lexical_weight=(
            settings.retrieval_lexical_weight if lexical_weight is None else lexical_weight
        ),
        diversity=settings.retrieval_diversity_enabled if diversity is None else diversity,
        diversity_lambda=(
            settings.retrieval_diversity_lambda
            if diversity_lambda is None
            else diversity_lambda
        ),
        min_score=settings.retrieval_min_score if min_score is None else min_score,
    ).normalized()
    selected_groups = list(
        session.scalars(
            select(DocumentGroup).where(
                DocumentGroup.owner_id == owner_id,
                *( [DocumentGroup.id.in_(group_ids)] if group_ids else [] ),
            )
        )
    )
    vector_results = []
    for group in selected_groups:
        embedding_service = get_embedding_service_for_group(session, group.id, settings)
        vector_results.extend(
            vector_store.search(
                embedding_service.embed_query(query),
                limit=retrieval_options.candidate_limit,
                metadata_filter={"owner_id": owner_id, "group_id": group.id},
            )
        )
    ranked_results = rerank_vector_results(
        query=query,
        results=vector_results,
        options=retrieval_options,
    )

    filtered_results = []
    for ranked in ranked_results:
        result = ranked.result
        if group_ids and result.metadata.get("group_id") not in group_ids:
            continue
        document_id = str(result.metadata.get("document_id", ""))
        group_id = str(result.metadata.get("group_id", ""))
        if not document_id or not group_id:
            continue
        if get_document(
            session,
            document_id=document_id,
            group_id=group_id,
            owner_id=owner_id,
        ) is None:
            continue
        filtered_results.append(
            SearchResult(
                chunk_id=str(result.metadata.get("chunk_id", result.id)),
                document_id=document_id,
                group_id=group_id,
                text=result.text,
                score=ranked.final_score,
                vector_score=ranked.vector_score,
                lexical_score=ranked.lexical_score,
                metadata={
                    **result.metadata,
                    "retrieval": {
                        "rerank": retrieval_options.rerank,
                        "diversity": retrieval_options.diversity,
                        "candidate_limit": retrieval_options.candidate_limit,
                    },
                },
            )
        )

    return filtered_results[:limit]


def document_with_chunk_count(
    document: Document,
    *,
    processing_job_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": document.id,
        "owner_id": document.owner_id,
        "group_id": document.group_id,
        "title": document.title,
        "source_name": document.source_name,
        "content_type": document.content_type,
        "status": document.status,
        "error_message": document.error_message,
        "extra_metadata": document.extra_metadata,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "chunk_count": len(document.chunks),
        "processing_job_id": processing_job_id,
    }


def _clean_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str | int | float | bool)
    }
