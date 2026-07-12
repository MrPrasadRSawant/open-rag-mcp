from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDependency, SessionDependency
from app.schemas.documents import ProcessingJobRead
from app.services.jobs import get_processing_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ProcessingJobRead)
def get_job(
    job_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ProcessingJobRead:
    job = get_processing_job(session, job_id=job_id, owner_id=current_user.id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found",
        )

    return job
