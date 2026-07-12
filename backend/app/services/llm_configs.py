from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret
from app.models import DocumentGroup, LlmProviderConfig
from app.schemas.llm_configs import LlmConfigType, LlmProvider


def create_llm_provider_config(
    session: Session,
    *,
    user_id: str,
    secret_key: str,
    name: str,
    provider: LlmProvider,
    api_key: str,
    config_type: LlmConfigType,
    base_url: str | None = None,
    embedding_model: str | None = None,
    chat_model: str | None = None,
) -> LlmProviderConfig:
    existing = session.scalar(
        select(LlmProviderConfig.id).where(
            LlmProviderConfig.user_id == user_id,
            func.lower(LlmProviderConfig.name) == name.strip().lower(),
        )
    )
    if existing is not None:
        raise ValueError("A config with this name already exists")
    if provider == LlmProvider.internal:
        raise ValueError("Internal configs are managed by the system")
    if provider != LlmProvider.google:
        raise ValueError("Only the Google Gemini provider is currently supported")
    if config_type == LlmConfigType.embedding and not embedding_model:
        raise ValueError("Embedding model is required for an embedding config")
    if config_type == LlmConfigType.embedding and provider == LlmProvider.anthropic:
        raise ValueError("Anthropic does not provide an embedding API")
    if config_type == LlmConfigType.chat_llm and not chat_model:
        raise ValueError("Chat model is required for a chat LLM config")
    if provider in {LlmProvider.azure_openai, LlmProvider.custom} and not base_url:
        raise ValueError("Base URL is required for this provider")
    config = LlmProviderConfig(
        user_id=user_id,
        name=name.strip(),
        provider=provider.value,
        purpose=config_type.value,
        encrypted_api_key=encrypt_secret(api_key, secret_key=secret_key),
        api_key_hint=mask_api_key(api_key),
        base_url=base_url,
        embedding_model=embedding_model if config_type == LlmConfigType.embedding else None,
        chat_model=chat_model if config_type == LlmConfigType.chat_llm else None,
        is_active=True,
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def list_llm_provider_configs(session: Session, *, user_id: str) -> list[LlmProviderConfig]:
    return list(
        session.scalars(
            select(LlmProviderConfig)
            .where(LlmProviderConfig.user_id == user_id)
            .order_by(LlmProviderConfig.created_at.desc())
        )
    )


def get_llm_provider_config(
    session: Session,
    *,
    user_id: str,
    config_id: str,
) -> LlmProviderConfig | None:
    return session.scalar(
        select(LlmProviderConfig).where(
            LlmProviderConfig.id == config_id,
            LlmProviderConfig.user_id == user_id,
        )
    )


def delete_llm_provider_config(
    session: Session,
    *,
    user_id: str,
    config_id: str,
) -> LlmProviderConfig | None:
    config = get_llm_provider_config(session, user_id=user_id, config_id=config_id)
    if config is None:
        return None
    if config.provider == LlmProvider.internal.value:
        raise ValueError("The internal Default config cannot be deleted")
    if count_config_groups(session, config_id=config.id, user_id=user_id):
        raise ValueError("Delete the document groups using this config first")
    session.delete(config)
    session.commit()
    return config


def read_llm_provider_api_key(
    session: Session,
    *,
    user_id: str,
    config_id: str,
    secret_key: str,
) -> str | None:
    config = get_llm_provider_config(session, user_id=user_id, config_id=config_id)
    if config is None or not config.is_active or config.encrypted_api_key is None:
        return None
    return decrypt_secret(config.encrypted_api_key, secret_key=secret_key)


def get_or_create_default_embedding_config(
    session: Session, *, user_id: str, model_name: str
) -> LlmProviderConfig:
    config = session.scalar(
        select(LlmProviderConfig).where(
            LlmProviderConfig.user_id == user_id,
            LlmProviderConfig.provider == LlmProvider.internal.value,
            LlmProviderConfig.purpose == LlmConfigType.embedding.value,
        )
    )
    if config is not None:
        return config
    name = "Default"
    if session.scalar(
        select(LlmProviderConfig.id).where(
            LlmProviderConfig.user_id == user_id,
            func.lower(LlmProviderConfig.name) == name.lower(),
        )
    ):
        name = "Default (Internal)"
    config = LlmProviderConfig(
        user_id=user_id,
        name=name,
        provider=LlmProvider.internal.value,
        purpose=LlmConfigType.embedding.value,
        embedding_model=model_name,
        is_active=True,
    )
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def count_config_groups(session: Session, *, config_id: str, user_id: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(DocumentGroup).where(
                DocumentGroup.llm_config_id == config_id,
                DocumentGroup.owner_id == user_id,
            )
        )
        or 0
    )


def mask_api_key(api_key: str) -> str:
    cleaned = api_key.strip()
    if len(cleaned) <= 8:
        return "****"
    return f"{cleaned[:4]}...{cleaned[-4:]}"
