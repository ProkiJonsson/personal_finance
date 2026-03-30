from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/accounts", tags=["accounts"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class AccountCreate(BaseModel):
    """Тело запроса для создания счёта"""
    name: str
    balance: float = 0.0

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название счёта не может быть пустым")
        return v


class AccountUpdate(BaseModel):
    """Тело запроса для обновления счёта — все поля опциональны"""
    name: Optional[str] = None
    balance: Optional[float] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Название счёта не может быть пустым")
        return v


class AccountResponse(BaseModel):
    """Ответ с данными счёта"""
    id: int
    user_id: int
    name: str
    balance: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def _get_account_or_404(account_id: int, user_id: int, db: Session) -> models.Account:
    """Возвращает счёт пользователя или выбрасывает 404."""
    account = db.query(models.Account).filter(
        models.Account.id == account_id,
        models.Account.user_id == user_id,
    ).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Счёт не найден")
    return account


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[AccountResponse], summary="Список счетов текущего пользователя")
def list_accounts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Account]:
    return (
        db.query(models.Account)
        .filter(models.Account.user_id == current_user.id)
        .order_by(models.Account.created_at)
        .all()
    )


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED, summary="Создать счёт")
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Account:
    account = models.Account(user_id=current_user.id, **data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=AccountResponse, summary="Обновить счёт")
def update_account(
    account_id: int,
    data: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Account:
    account = _get_account_or_404(account_id, current_user.id, db)

    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить счёт")
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    account = _get_account_or_404(account_id, current_user.id, db)
    db.delete(account)
    db.commit()
