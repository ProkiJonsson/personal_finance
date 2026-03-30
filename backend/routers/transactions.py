from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/transactions", tags=["transactions"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class TransactionCreate(BaseModel):
    """Тело запроса для создания транзакции"""
    date: datetime
    amount: float
    type: models.TransactionType
    fund_id: int
    account_id: Optional[int] = None
    category_id: int
    comment: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Сумма транзакции должна быть положительной")
        return v


class TransactionUpdate(BaseModel):
    """Тело запроса для обновления транзакции — все поля опциональны"""
    date: Optional[datetime] = None
    amount: Optional[float] = None
    type: Optional[models.TransactionType] = None
    fund_id: Optional[int] = None
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("Сумма транзакции должна быть положительной")
        return v


class TransactionResponse(BaseModel):
    """Ответ с данными транзакции"""
    id: int
    user_id: int
    date: datetime
    amount: float
    type: models.TransactionType
    fund_id: int
    account_id: Optional[int]
    category_id: Optional[int]
    comment: Optional[str]
    is_initial: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class InitialBalanceItem(BaseModel):
    fund_id: int
    account_id: Optional[int] = None
    amount: float
    date: datetime

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Сумма должна быть положительной")
        return v


class InitialBalancesRequest(BaseModel):
    items: List[InitialBalanceItem]


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def _get_transaction_or_404(transaction_id: int, user_id: int, db: Session) -> models.Transaction:
    """Возвращает транзакцию пользователя или выбрасывает 404."""
    transaction = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == user_id,
    ).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Транзакция не найдена")
    return transaction


def _verify_related_objects(
    user_id: int,
    fund_id: int,
    category_id: Optional[int],
    account_id: Optional[int],
    db: Session,
) -> None:
    """
    Проверяет, что fund, category и account (если указан)
    существуют и принадлежат пользователю.
    """
    fund = db.query(models.Fund).filter(
        models.Fund.id == fund_id,
        models.Fund.user_id == user_id,
    ).first()
    if not fund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фонд не найден")

    if category_id is not None:
        category = db.query(models.Category).filter(
            models.Category.id == category_id,
            models.Category.user_id == user_id,
        ).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")

    if account_id is not None:
        account = db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.user_id == user_id,
        ).first()
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Счёт не найден")


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[TransactionResponse], summary="Список транзакций с фильтрами")
def list_transactions(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    fund_id: Optional[int] = None,
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    type: Optional[models.TransactionType] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Transaction]:
    """
    Возвращает транзакции текущего пользователя.

    Все фильтры опциональны и комбинируются:
    - date_from / date_to — диапазон по полю date (включительно)
    - fund_id — транзакции конкретного фонда
    - account_id — транзакции конкретного счёта
    - category_id — транзакции конкретной категории
    - type — income или expense
    """
    query = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id
    )

    if date_from is not None:
        query = query.filter(models.Transaction.date >= date_from)
    if date_to is not None:
        query = query.filter(models.Transaction.date <= date_to)
    if fund_id is not None:
        query = query.filter(models.Transaction.fund_id == fund_id)
    if account_id is not None:
        query = query.filter(models.Transaction.account_id == account_id)
    if category_id is not None:
        query = query.filter(models.Transaction.category_id == category_id)
    if type is not None:
        query = query.filter(models.Transaction.type == type)

    return query.order_by(models.Transaction.date.desc(), models.Transaction.id.desc()).all()


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, summary="Создать транзакцию")
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Transaction:
    _verify_related_objects(current_user.id, data.fund_id, data.category_id, data.account_id, db)

    transaction = models.Transaction(user_id=current_user.id, **data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse, summary="Обновить транзакцию")
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Transaction:
    transaction = _get_transaction_or_404(transaction_id, current_user.id, db)

    updates = data.model_dump(exclude_none=True)

    # Если меняются fund/account/category — проверяем итоговые значения после слияния
    new_fund_id = updates.get("fund_id", transaction.fund_id)
    new_category_id = updates.get("category_id", transaction.category_id)
    # account_id может быть явно обнулён через None в теле — используем exclude_unset
    new_account_id = data.account_id if "account_id" in data.model_fields_set else transaction.account_id

    if any(k in updates for k in ("fund_id", "account_id", "category_id")):
        _verify_related_objects(current_user.id, new_fund_id, new_category_id, new_account_id, db)

    for field, value in updates.items():
        setattr(transaction, field, value)

    # Отдельно обрабатываем явное обнуление account_id
    if "account_id" in data.model_fields_set and data.account_id is None:
        transaction.account_id = None

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить транзакцию")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    transaction = _get_transaction_or_404(transaction_id, current_user.id, db)
    db.delete(transaction)
    db.commit()


@router.get("/initial-balances", response_model=list[TransactionResponse], summary="Получить начальные остатки")
def get_initial_balances(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Transaction]:
    return db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_initial == True,
    ).all()


@router.post("/initial-balances", response_model=list[TransactionResponse], status_code=status.HTTP_201_CREATED, summary="Сохранить начальные остатки")
def save_initial_balances(
    data: InitialBalancesRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Transaction]:
    """
    Удаляет существующие начальные остатки пользователя и создаёт новые.
    Каждый элемент: {fund_id, account_id?, amount, date}.
    """
    # Удаляем старые начальные остатки
    db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_initial == True,
    ).delete()

    created = []
    for item in data.items:
        # Проверяем fund и account
        fund = db.query(models.Fund).filter(
            models.Fund.id == item.fund_id,
            models.Fund.user_id == current_user.id,
        ).first()
        if not fund:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Фонд {item.fund_id} не найден")

        if item.account_id is not None:
            account = db.query(models.Account).filter(
                models.Account.id == item.account_id,
                models.Account.user_id == current_user.id,
            ).first()
            if not account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Счёт {item.account_id} не найден")

        tx = models.Transaction(
            user_id=current_user.id,
            date=item.date,
            amount=item.amount,
            type=models.TransactionType.income,
            fund_id=item.fund_id,
            account_id=item.account_id,
            category_id=None,
            is_initial=True,
        )
        db.add(tx)
        created.append(tx)

    db.commit()
    for tx in created:
        db.refresh(tx)
    return created
