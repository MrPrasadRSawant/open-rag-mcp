from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDependency, SessionDependency, SettingsDependency
from app.schemas.llm_configs import LlmProviderConfigCreate, LlmProviderConfigRead
from app.services.llm_configs import (
    count_config_groups,
    create_llm_provider_config,
    delete_llm_provider_config,
    get_or_create_default_embedding_config,
    list_llm_provider_configs,
)

router = APIRouter(prefix="/llm-configs", tags=["llm-configs"])


@router.post(
    "",
    response_model=LlmProviderConfigRead,
    status_code=status.HTTP_201_CREATED,
)
def create_config(
    payload: LlmProviderConfigCreate,
    session: SessionDependency,
    settings: SettingsDependency,
    current_user: CurrentUserDependency,
) -> LlmProviderConfigRead:
    try:
        return create_llm_provider_config(
            session,
            user_id=current_user.id,
            secret_key=settings.secret_key,
            name=payload.name,
            provider=payload.provider,
            config_type=payload.config_type,
            api_key=payload.api_key,
            base_url=payload.base_url,
            embedding_model=payload.embedding_model,
            chat_model=payload.chat_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[LlmProviderConfigRead])
def list_configs(
    session: SessionDependency,
    current_user: CurrentUserDependency,
    settings: SettingsDependency,
) -> list[LlmProviderConfigRead]:
    get_or_create_default_embedding_config(
        session, user_id=current_user.id, model_name=settings.embedding_model_name
    )
    configs = list_llm_provider_configs(session, user_id=current_user.id)
    return [
        LlmProviderConfigRead.model_validate(config).model_copy(
            update={
                "in_use_by_groups": count_config_groups(
                    session, config_id=config.id, user_id=current_user.id
                )
            }
        )
        for config in configs
    ]


@router.delete("/{config_id}", response_model=LlmProviderConfigRead)
def delete_config(
    config_id: str,
    session: SessionDependency,
    current_user: CurrentUserDependency,
) -> LlmProviderConfigRead:
    try:
        config = delete_llm_provider_config(session, user_id=current_user.id, config_id=config_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM provider config not found",
        )
    return config
