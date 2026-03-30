from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum,
    ForeignKey, CheckConstraint, Text, Boolean
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from database import Base
import enum


# ──────────────────────────────────────────────
# Перечисления (enum-типы)
# ──────────────────────────────────────────────

class FundType(str, enum.Enum):
    """Тип фонда: текущий или инвестиционный"""
    current = "current"
    investment = "investment"


class CategoryType(str, enum.Enum):
    """Тип категории: доход или расход"""
    income = "income"
    expense = "expense"


class TransactionType(str, enum.Enum):
    """Тип транзакции: доход или расход"""
    income = "income"
    expense = "expense"


# ──────────────────────────────────────────────
# Модели таблиц
# ──────────────────────────────────────────────

class User(Base):
    """Пользователи системы"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    funds = relationship("Fund", back_populates="user", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")


class Fund(Base):
    """Фонды пользователя (текущий / инвестиционный)"""
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(FundType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    user = relationship("User", back_populates="funds")
    transactions = relationship("Transaction", back_populates="fund")


class Account(Base):
    """Счета пользователя — физическое хранилище денег (карта, наличные и т.п.)"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")


class Category(Base):
    """
    Категории доходов/расходов с иерархией до 4 уровней.
    parent_id ссылается на запись в этой же таблице (self-reference).
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(CategoryType), nullable=True)
    # Уровень иерархии: от 1 (корневая) до 4 (самая вложенная)
    level = Column(Integer, nullable=False, default=1)
    # Родительская категория (NULL для корневых категорий)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    # Порядок сортировки внутри одного уровня
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Уровень должен быть от 1 до 4
        CheckConstraint("level >= 1 AND level <= 4", name="ck_categories_level"),
    )

    # Связи
    user = relationship("User", back_populates="categories")
    # Self-referential связи для иерархии категорий.
    # remote_side=[id] на стороне parent указывает SQLAlchemy что id — «родительская» сторона,
    # а parent_id — «дочерняя». Без этого он не может определить направление.
    children = relationship(
        "Category",
        back_populates="parent",
        foreign_keys=[parent_id],
    )
    parent = relationship(
        "Category",
        back_populates="children",
        foreign_keys=[parent_id],
        remote_side="[Category.id]",
    )
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    """Финансовые транзакции (доходы и расходы)"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Дата проведения транзакции (может отличаться от created_at)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    # Сумма всегда положительная; тип определяет направление
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    fund_id = Column(Integer, ForeignKey("funds.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Счёт необязателен — транзакция может быть на уровне фонда
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)
    comment = Column(Text, nullable=True)
    is_initial = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Сумма должна быть строго положительной
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    # Связи
    user = relationship("User", back_populates="transactions")
    fund = relationship("Fund", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
