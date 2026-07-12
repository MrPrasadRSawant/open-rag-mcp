from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.security import TokenError, decode_access_token
from app.models import User
from app.services.auth import get_user_by_id
from app.services.vector_store.base import VectorStore
from app.services.vector_store.factory import get_vector_store

SettingsDependency = Annotated[Settings, Depends(get_settings)]
SessionDependency = Annotated[Session, Depends(get_session)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_vector_store_dependency(settings: SettingsDependency) -> VectorStore:
    return get_vector_store(settings)


VectorStoreDependency = Annotated[VectorStore, Depends(get_vector_store_dependency)]


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDependency,
    settings: SettingsDependency,
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token, secret_key=settings.secret_key)
    except TokenError as exc:
        raise credentials_error from exc

    user = get_user_by_id(session, str(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error

    return user


CurrentUserDependency = Annotated[User, Depends(get_current_user)]
