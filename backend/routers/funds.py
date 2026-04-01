from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/funds", tags=["funds"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class FundCreate(BaseModel):
    """Тело запроса для создания фонда"""
    name: str
    type: models.FundType

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название фонда не может быть пустым")
        return v


class FundUpdate(BaseModel):
    """Тело запроса для обновления фонда — все поля опциональны"""
    name: Optional[str] = None
    type: Optional[models.FundType] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Название фонда не может быть пустым")
        return v


class FundResponse(BaseModel):
    """Ответ с данными фонда. Баланс считается динамически из транзакций."""
    id: int
    user_id: int
    name: str
    type: models.FundType
    balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def _get_fund_or_404(fund_id: int, user_id: int, db: Session) -> models.Fund:
    """Возвращает фонд пользователя или выбрасывает 404."""
    fund = db.query(models.Fund).filter(
        models.Fund.id == fund_id,
        models.Fund.user_id == user_id,
    ).first()
    if not fund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фонд не найден")
    return fund


def _calc_balances(user_id: int, db: Session) -> dict[int, float]:
    """
    Возвращает словарь {fund_id: balance} для всех фондов пользователя.
    Баланс = сумма income - сумма expense по транзакциям фонда.
    """
    rows = (
        db.query(
            models.Transaction.fund_id,
            func.coalesce(
                func.sum(
                    case(
                        (models.Transaction.type == models.TransactionType.income, models.Transaction.amount),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (models.Transaction.type == models.TransactionType.expense, models.Transaction.amount),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("expense"),
        )
        .filter(models.Transaction.user_id == user_id)
        .group_by(models.Transaction.fund_id)
        .all()
    )
    return {row.fund_id: row.income - row.expense for row in rows}


def _fund_to_response(fund: models.Fund, balances: dict[int, float]) -> FundResponse:
    return FundResponse(
        id=fund.id,
        user_id=fund.user_id,
        name=fund.name,
        type=fund.type,
        balance=balances.get(fund.id, 0.0),
        created_at=fund.created_at,
    )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[FundResponse], summary="Список фондов текущего пользователя")
def list_funds(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[FundResponse]:
    funds = (
        db.query(models.Fund)
        .filter(models.Fund.user_id == current_user.id)
        .order_by(models.Fund.created_at)
        .all()
    )
    balances = _calc_balances(current_user.id, db)
    return [_fund_to_response(f, balances) for f in funds]


@router.post("", response_model=FundResponse, status_code=status.HTTP_201_CREATED, summary="Создать фонд")
def create_fund(
    data: FundCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> FundResponse:
    fund = models.Fund(user_id=current_user.id, **data.model_dump())
    db.add(fund)
    db.commit()
    db.refresh(fund)
    return _fund_to_response(fund, {})


@router.put("/{fund_id}", response_model=FundResponse, summary="Обновить фонд")
def update_fund(
    fund_id: int,
    data: FundUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> FundResponse:
    fund = _get_fund_or_404(fund_id, current_user.id, db)

    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(fund, field, value)

    db.commit()
    db.refresh(fund)
    balances = _calc_balances(current_user.id, db)
    return _fund_to_response(fund, balances)


@router.delete("/{fund_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить фонд")
def delete_fund(
    fund_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    fund = _get_fund_or_404(fund_id, current_user.id, db)
    try:
        db.delete(fund)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить фонд: есть связанные операции",
        )
