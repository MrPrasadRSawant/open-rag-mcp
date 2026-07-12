from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import TokenResponse, UserCreate


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def create_user(session: Session, payload: UserCreate) -> User:
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("A user with this email already exists") from exc

    session.refresh(user)
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User | None:
    user = get_user_by_email(session, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_token_response(user: User, settings: Settings) -> TokenResponse:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=user.id,
        secret_key=settings.secret_key,
        expires_delta=expires_delta,
    )
    return TokenResponse(
        access_token=token,
        expires_in=int(expires_delta.total_seconds()),
        user=user,
    )
