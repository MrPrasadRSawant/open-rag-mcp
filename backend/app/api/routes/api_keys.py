from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDependency, SessionDependency
from app.schemas.api_keys import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyRead
from app.services.api_keys import create_api_key, list_api_keys, revoke_api_key

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_key(
    payload: ApiKeyCreate,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ApiKeyCreateResponse:
    try:
        api_key, raw_key = create_api_key(
            session,
            user_id=current_user.id,
            group_id=payload.group_id,
            name=payload.name,
            expires_at=payload.expires_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    data = ApiKeyRead.model_validate(api_key).model_dump()
    return ApiKeyCreateResponse(**data, api_key=raw_key)


@router.get("", response_model=list[ApiKeyRead])
def list_keys(
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> list[ApiKeyRead]:
    return list_api_keys(session, user_id=current_user.id)


@router.delete("/{api_key_id}", response_model=ApiKeyRead)
def revoke_key(
    api_key_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> ApiKeyRead:
    api_key = revoke_api_key(session, user_id=current_user.id, api_key_id=api_key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return api_key
