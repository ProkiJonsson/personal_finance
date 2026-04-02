from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from database import get_db
from auth import hash_password, verify_password, create_access_token
import models

router = APIRouter(prefix="/auth", tags=["auth"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Тело запроса для регистрации нового пользователя"""
    name: str
    email: EmailStr
    password: str

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Пароль должен содержать не менее 6 символов")
        return v


class LoginRequest(BaseModel):
    """Тело запроса для входа по email и паролю"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Ответ с JWT-токеном после успешной авторизации"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Создаёт нового пользователя и возвращает JWT-токен.
    Возвращает 409 если пользователь с таким email уже существует.
    """
    # Проверка уникальности email
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже зарегистрирован",
        )

    user = models.User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, name=user.name)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход по email и паролю",
)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Проверяет email и пароль, возвращает JWT-токен.
    Возвращает 401 при неверных учётных данных (намеренно без уточнения — email или пароль).
    """
    user = db.query(models.User).filter(models.User.email == data.email).first()

    # Проверяем пользователя и пароль единым условием,
    # чтобы не раскрывать информацию о существовании email
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id, name=user.name)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email,
    )
