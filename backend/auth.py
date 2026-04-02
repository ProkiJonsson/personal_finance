from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
import models

# ──────────────────────────────────────────────
# Конфигурация
# ──────────────────────────────────────────────

# Секретный ключ для подписи JWT. В продакшене — загружать из переменной окружения.
# Сгенерировать: openssl rand -hex 32
SECRET_KEY = "замените-на-случайную-строку-в-продакшене"
ALGORITHM = "HS256"
# Время жизни access-токена в минутах
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 часа

# ──────────────────────────────────────────────
# Хеширование паролей
# ──────────────────────────────────────────────

# CryptContext с bcrypt — рекомендуемый алгоритм хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Схема OAuth2 — FastAPI будет искать токен в заголовке Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля для сохранения в БД."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Сравнивает открытый пароль с хешем. Возвращает True если совпадают."""
    return pwd_context.verify(plain_password, hashed_password)


# ──────────────────────────────────────────────
# JWT токены
# ──────────────────────────────────────────────

def create_access_token(user_id: str, name: str = "", expires_delta: Optional[timedelta] = None) -> str:
    """
    Создаёт подписанный JWT access-токен.

    Payload содержит:
      sub  — идентификатор пользователя (строка, стандартное поле JWT)
      name — отображаемое имя пользователя
      exp  — время истечения токена
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "name": name,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[str]:
    """
    Декодирует JWT и возвращает user_id.
    Возвращает None если токен невалиден или истёк.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            return None
        return user_id_str
    except JWTError:
        return None


# ──────────────────────────────────────────────
# FastAPI dependency
# ──────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Dependency для защищённых роутеров.
    Извлекает пользователя из JWT-токена и проверяет его существование в БД.

    Использование:
        @router.get("/me")
        def get_me(user: models.User = Depends(get_current_user)):
            ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = _decode_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user
