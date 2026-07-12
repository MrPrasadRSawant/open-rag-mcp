from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUserDependency, SessionDependency, SettingsDependency
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services.auth import authenticate_user, create_token_response, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: UserCreate,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    try:
        user = create_user(session, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return create_token_response(user, settings)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    session: SessionDependency,
    settings: SettingsDependency,
) -> TokenResponse:
    user = authenticate_user(session, email=payload.email, password=payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return create_token_response(user, settings)


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUserDependency) -> UserRead:
    return current_user
