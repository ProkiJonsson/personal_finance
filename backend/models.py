from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, Date,
    ForeignKey, CheckConstraint, Text, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from database import Base
import enum


# ──────────────────────────────────────────────
# Перечисления (enum-типы)
# ──────────────────────────────────────────────

class FundType(str, enum.Enum):
    """Тип фонда"""
    budget = "budget"            # Бюджетный (каскадное наполнение)
    investment = "investment"    # Инвестиционный (накопитель)
    tax_reserve = "tax_reserve"  # Налоговый резерв
    debt = "debt"                # Долг (я должен кому-то, баланс −)
    loan = "loan"                # Займ (мне должны, баланс +)
    placement = "placement"      # Размещение инвестиций (вклады, брокер)


class CategoryType(str, enum.Enum):
    """Тип категории: доход или расход"""
    income = "income"
    expense = "expense"


class TransactionType(str, enum.Enum):
    """Тип транзакции: доход или расход"""
    income = "income"
    expense = "expense"


class AttachmentEntityType(str, enum.Enum):
    """К чему привязано вложение"""
    contract = "contract"
    transaction = "transaction"


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
    counterparties = relationship("Counterparty", back_populates="user", cascade="all, delete-orphan")
    cascades = relationship("Cascade", back_populates="user", cascade="all, delete-orphan")
    tax_settings = relationship("TaxSetting", back_populates="user", cascade="all, delete-orphan")
    app_setting = relationship("AppSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="user", cascade="all, delete-orphan")


# ──── Контрагенты и договоры ─────────────────

class Counterparty(Base):
    """Контрагент: банк, заёмщик, кредитор и т.п."""
    __tablename__ = "counterparties"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="counterparties")
    contracts = relationship("Contract", back_populates="counterparty", cascade="all, delete-orphan")


class Contract(Base):
    """Договор контрагента. При создании контрагента автоматически создаётся 'Основной'."""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    counterparty_id = Column(Integer, ForeignKey("counterparties.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, default="Основной")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    counterparty = relationship("Counterparty", back_populates="contracts")
    funds = relationship("Fund", back_populates="contract")
    attachments_rel = relationship(
        "Attachment",
        primaryjoin="and_(Attachment.entity_type=='contract', foreign(Attachment.entity_id)==Contract.id)",
        viewonly=True,
    )


# ──── Фонды ──────────────────────────────────

class Fund(Base):
    """Фонды пользователя (6 типов)"""
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(Enum(FundType), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, index=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связи
    user = relationship("User", back_populates="funds")
    contract = relationship("Contract", back_populates="funds")
    transactions = relationship("Transaction", back_populates="fund")
    cascade_slots = relationship("CascadeSlot", back_populates="fund")
    split_rules_target = relationship("SplitRule", back_populates="target_fund")


# ──── Счета ──────────────────────────────────

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


# ──── Категории ──────────────────────────────

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
    level = Column(Integer, nullable=False, default=1)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("level >= 1 AND level <= 4", name="ck_categories_level"),
    )

    # Связи
    user = relationship("User", back_populates="categories")
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


# ──── Транзакции ─────────────────────────────

class Transaction(Base):
    """Финансовые транзакции (доходы и расходы)"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    # fund_id теперь nullable — когда учёт по фондам выключен
    fund_id = Column(Integer, ForeignKey("funds.id", ondelete="RESTRICT"), nullable=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=True, index=True)
    comment = Column(Text, nullable=True)
    is_initial = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    # Связи
    user = relationship("User", back_populates="transactions")
    fund = relationship("Fund", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")


# ──── Каскады (расклад) ─────────────────────

class Cascade(Base):
    """Конфигурация каскадного распределения дохода. Действует с effective_from."""
    __tablename__ = "cascades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    effective_from = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="cascades")
    slots = relationship("CascadeSlot", back_populates="cascade", cascade="all, delete-orphan",
                         order_by="CascadeSlot.sort_order")
    split_rules = relationship("SplitRule", back_populates="cascade", cascade="all, delete-orphan")


class CascadeSlot(Base):
    """Позиция фонда в каскаде с целевой суммой."""
    __tablename__ = "cascade_slots"

    id = Column(Integer, primary_key=True, index=True)
    cascade_id = Column(Integer, ForeignKey("cascades.id", ondelete="CASCADE"), nullable=False, index=True)
    fund_id = Column(Integer, ForeignKey("funds.id", ondelete="CASCADE"), nullable=False, index=True)
    target_amount = Column(Float, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)

    cascade = relationship("Cascade", back_populates="slots")
    fund = relationship("Fund", back_populates="cascade_slots")


class SplitRule(Base):
    """
    Правило отщепления % дохода в указанный фонд.
    trigger_position:
      NULL  — от каждого рубля (до наполнения любого фонда)
      0..N  — после наполнения фонда на данной позиции в каскаде
      -1    — после наполнения ВСЕХ фондов каскада
    """
    __tablename__ = "split_rules"

    id = Column(Integer, primary_key=True, index=True)
    cascade_id = Column(Integer, ForeignKey("cascades.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_position = Column(Integer, nullable=True)
    target_fund_id = Column(Integer, ForeignKey("funds.id", ondelete="CASCADE"), nullable=False, index=True)
    percentage = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("percentage > 0 AND percentage <= 1", name="ck_split_rules_percentage"),
    )

    cascade = relationship("Cascade", back_populates="split_rules")
    target_fund = relationship("Fund", back_populates="split_rules_target")


# ──── Настройки НДФЛ ────────────────────────

class TaxSetting(Base):
    """Настройки НДФЛ на доход от вкладов по годам."""
    __tablename__ = "tax_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    tax_free_threshold = Column(Float, nullable=False)
    rate_standard = Column(Float, nullable=False, default=0.13)
    rate_elevated = Column(Float, nullable=False, default=0.15)
    elevated_threshold = Column(Float, nullable=False, default=2000000.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "year", name="uq_tax_settings_user_year"),
    )

    user = relationship("User", back_populates="tax_settings")


# ──── Настройки приложения ───────────────────

class AppSetting(Base):
    """Настройки пользователя (учёт по фондам, лимит вложений)."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    fund_accounting_enabled = Column(Boolean, nullable=False, default=False)
    max_attachment_size_mb = Column(Integer, nullable=False, default=10)

    user = relationship("User", back_populates="app_setting")


# ──── Вложения (файлы) ──────────────────────

class Attachment(Base):
    """Вложения файлов (PDF, JPEG, PNG) к договорам и операциям."""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(Enum(AttachmentEntityType), nullable=False)
    entity_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="attachments")
