"""Authentication routes for Cipher Frame."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth_dependencies import get_current_user, require_admin, require_client
from backend.schemas.auth_schema import AuthUserResponse, Token, UserLogin, UserRegister
from backend.schemas.user_schema import UserRead
from backend.services.auth_service import authenticate_user, register_user, user_to_read_schema

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, request: Request, db: Session = Depends(get_db)) -> UserRead:
    """Register a new client account."""

    return register_user(db, payload, ip_address=request.client.host if request.client else None)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    """Authenticate a user and issue a JWT access token."""

    _, token = authenticate_user(db, payload, ip_address=request.client.host if request.client else None)
    return Token(access_token=token)


@router.get("/me", response_model=UserRead)
def read_me(current_user=Depends(get_current_user)) -> UserRead:
    """Return the currently authenticated user."""

    return user_to_read_schema(current_user)


@router.get("/admin-check", response_model=dict[str, str])
def admin_check(current_user=Depends(require_admin)) -> dict[str, str]:
    """Test route for admin-only access."""

    return {"status": "ok", "role": current_user.role.value}


@router.get("/client-check", response_model=dict[str, str])
def client_check(current_user=Depends(require_client)) -> dict[str, str]:
    """Test route for client-only access."""

    return {"status": "ok", "role": current_user.role.value}