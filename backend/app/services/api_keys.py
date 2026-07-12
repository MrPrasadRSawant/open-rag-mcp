import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiKey
from app.services.documents import get_document_group

API_KEY_PREFIX = "ormcp"


def generate_api_key() -> str:
    return f"{API_KEY_PREFIX}_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def key_prefix(api_key: str) -> str:
    return api_key[:18]


def create_api_key(
    session: Session,
    *,
    user_id: str,
    group_id: str,
    name: str,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    group = get_document_group(session, group_id=group_id, owner_id=user_id)
    if group is None:
        raise ValueError("document group not found")

    raw_key = generate_api_key()
    api_key = ApiKey(
        user_id=user_id,
        group_id=group_id,
        name=name,
        key_prefix=key_prefix(raw_key),
        key_hash=hash_api_key(raw_key),
        expires_at=expires_at,
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return api_key, raw_key


def list_api_keys(session: Session, *, user_id: str) -> list[ApiKey]:
    return list(
        session.scalars(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
    )


def revoke_api_key(session: Session, *, user_id: str, api_key_id: str) -> ApiKey | None:
    api_key = session.scalar(
        select(ApiKey).where(
            ApiKey.id == api_key_id,
            ApiKey.user_id == user_id,
        )
    )
    if api_key is None:
        return None

    api_key.revoked_at = datetime.now(UTC)
    session.commit()
    session.refresh(api_key)
    return api_key


def authenticate_api_key(session: Session, raw_key: str) -> ApiKey | None:
    prefix = key_prefix(raw_key)
    hashed_key = hash_api_key(raw_key)
    api_key = session.scalar(
        select(ApiKey).where(
            ApiKey.key_prefix == prefix,
            ApiKey.key_hash == hashed_key,
            ApiKey.revoked_at.is_(None),
        )
    )
    if api_key is None:
        return None

    now = datetime.now(UTC)
    if api_key.expires_at is not None and api_key.expires_at < now:
        return None

    api_key.last_used_at = now
    session.commit()
    session.refresh(api_key)
    return api_key
