from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import Settings
from app.core.database import get_session_maker
from app.models import Document, ProcessingJob
from app.services.documents import index_document_text
from app.services.extraction import extract_text
from app.services.ocr import get_ocr_engine
from app.services.vector_store.factory import get_vector_store


def get_processing_job(
    session,
    *,
    job_id: str,
    owner_id: str,
) -> ProcessingJob | None:
    return session.scalar(
        select(ProcessingJob).where(
            ProcessingJob.id == job_id,
            ProcessingJob.owner_id == owner_id,
        )
    )


def process_job(job_id: str, settings: Settings) -> None:
    session_maker = get_session_maker(settings.resolved_database_url)
    with session_maker() as session:
        job = session.get(ProcessingJob, job_id)
        if job is None or job.status not in {"queued", "failed"}:
            return

        document = session.get(Document, job.document_id)
        if document is None:
            job.status = "failed"
            job.error_message = "Document not found"
            job.started_at = job.started_at or datetime.now(UTC)
            job.completed_at = datetime.now(UTC)
            session.commit()
            return

        job.status = "processing"
        job.error_message = None
        job.started_at = datetime.now(UTC)
        document.status = "processing"
        document.error_message = None
        session.commit()

        try:
            text = _load_job_text(job, settings)
            vector_store = get_vector_store(settings)
            index_document_text(
                session,
                vector_store=vector_store,
                settings=settings,
                document=document,
                text=text,
                metadata=job.payload.get("metadata", {}),
            )
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
            job.error_message = None
            session.commit()
        except Exception as exc:
            session.rollback()
            job = session.get(ProcessingJob, job_id)
            document = session.get(Document, job.document_id) if job is not None else None
            if job is not None:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(UTC)
            if document is not None:
                document.status = "failed"
                document.error_message = str(exc)
            session.commit()


def _load_job_text(job: ProcessingJob, settings: Settings) -> str:
    if job.job_type == "text_ingestion":
        text = job.payload.get("text")
        if not isinstance(text, str):
            raise ValueError("Text ingestion job is missing text payload")
        return text

    if job.job_type == "upload_ingestion":
        storage_path = job.payload.get("storage_path")
        content_type = job.payload.get("content_type")
        if not isinstance(storage_path, str) or not isinstance(content_type, str):
            raise ValueError("Upload ingestion job is missing file payload")
        return extract_text(
            Path(storage_path),
            content_type=content_type,
            ocr_engine=get_ocr_engine(settings),
            ocr_pdf_dpi=settings.ocr_pdf_dpi,
        )

    raise ValueError(f"Unsupported processing job type: {job.job_type}")
