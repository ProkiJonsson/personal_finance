"""
Фикстуры для тестов: in-memory SQLite, тестовый клиент, авторизация.
"""
import sys
from pathlib import Path

# backend/ должен быть в sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database import Base, get_db
from main import app
from auth import hash_password, create_access_token
from sqlalchemy import text as sa_text
import models


# In-memory SQLite для тестов — StaticPool чтобы все соединения видели одну БД
TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


# Включаем FK constraints для SQLite
@event.listens_for(TEST_ENGINE, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db():
    """Пересоздаёт таблицы и возвращает сессию с FK constraints."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestSession()
    # Гарантируем FK constraints на текущем соединении
    session.execute(sa_text("PRAGMA foreign_keys=ON"))
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture
def client(db):
    """TestClient с подменённой БД."""
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user(db) -> models.User:
    """Создаёт тестового пользователя."""
    u = models.User(
        name="Тест",
        email="test@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def token(user) -> str:
    """JWT-токен тестового пользователя."""
    return create_access_token(user.id, user.name, is_active=True)


@pytest.fixture
def auth_headers(token) -> dict:
    """Заголовки авторизации."""
    return {"Authorization": f"Bearer {token}"}
