from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Путь к файлу базы данных — папка backend/
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR}/finance.db"

# Engine для SQLite.
# check_same_thread=False обязателен для SQLite при работе с FastAPI,
# т.к. запросы могут выполняться в разных потоках.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    # echo=True включить для отладки SQL-запросов
    echo=False,
)

# Фабрика сессий — используется для создания сессий БД в запросах
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей SQLAlchemy
Base = declarative_base()


def get_db():
    """
    Dependency для FastAPI.
    Открывает сессию БД на время обработки запроса и закрывает её после.

    Использование в роутере:
        @router.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Создаёт все таблицы, описанные в моделях, если они ещё не существуют.
    Импорт моделей должен быть выполнен ДО вызова этой функции,
    чтобы их метаданные попали в Base.metadata.
    """
    # Импорт здесь гарантирует регистрацию всех моделей в Base.metadata
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
