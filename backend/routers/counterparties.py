from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/counterparties", tags=["counterparties"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class CounterpartyCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название контрагента не может быть пустым")
        return v


class CounterpartyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Название контрагента не может быть пустым")
        return v


class ContractCreate(BaseModel):
    name: str = "Основной"
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название договора не может быть пустым")
        return v


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ContractResponse(BaseModel):
    id: int
    counterparty_id: int
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CounterpartyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    balance: float
    contracts: list[ContractResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class CounterpartyListItem(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    balance: float
    contracts_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_counterparty_or_404(cp_id: int, user_id: int, db: Session) -> models.Counterparty:
    cp = db.query(models.Counterparty).filter(
        models.Counterparty.id == cp_id,
        models.Counterparty.user_id == user_id,
    ).first()
    if not cp:
        raise HTTPException(status_code=404, detail="Контрагент не найден")
    return cp


def _calc_counterparty_balances(user_id: int, db: Session) -> dict[int, float]:
    """Словарь {counterparty_id: balance} через contracts → funds → transactions."""
    rows = (
        db.query(
            models.Counterparty.id.label("cp_id"),
            func.coalesce(
                func.sum(
                    case(
                        (models.Transaction.type == models.TransactionType.income, models.Transaction.amount),
                        else_=0.0,
                    )
                ), 0.0
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (models.Transaction.type == models.TransactionType.expense, models.Transaction.amount),
                        else_=0.0,
                    )
                ), 0.0
            ).label("expense"),
        )
        .join(models.Contract, models.Contract.counterparty_id == models.Counterparty.id)
        .join(models.Fund, models.Fund.contract_id == models.Contract.id)
        .join(models.Transaction, models.Transaction.fund_id == models.Fund.id)
        .filter(models.Counterparty.user_id == user_id)
        .group_by(models.Counterparty.id)
        .all()
    )
    return {row.cp_id: row.income - row.expense for row in rows}


# ──────────────────────────────────────────────
# Counterparty endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[CounterpartyListItem], summary="Список контрагентов")
def list_counterparties(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[CounterpartyListItem]:
    cps = (
        db.query(models.Counterparty)
        .options(joinedload(models.Counterparty.contracts))
        .filter(models.Counterparty.user_id == current_user.id)
        .order_by(models.Counterparty.name)
        .all()
    )
    balances = _calc_counterparty_balances(current_user.id, db)
    return [
        CounterpartyListItem(
            id=cp.id,
            user_id=cp.user_id,
            name=cp.name,
            description=cp.description,
            balance=balances.get(cp.id, 0.0),
            contracts_count=len(cp.contracts),
            created_at=cp.created_at,
        )
        for cp in cps
    ]


@router.get("/{cp_id}", response_model=CounterpartyResponse, summary="Детали контрагента")
def get_counterparty(
    cp_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CounterpartyResponse:
    cp = (
        db.query(models.Counterparty)
        .options(joinedload(models.Counterparty.contracts))
        .filter(models.Counterparty.id == cp_id, models.Counterparty.user_id == current_user.id)
        .first()
    )
    if not cp:
        raise HTTPException(status_code=404, detail="Контрагент не найден")
    balances = _calc_counterparty_balances(current_user.id, db)
    return CounterpartyResponse(
        id=cp.id,
        user_id=cp.user_id,
        name=cp.name,
        description=cp.description,
        balance=balances.get(cp.id, 0.0),
        contracts=[ContractResponse.model_validate(c) for c in cp.contracts],
        created_at=cp.created_at,
    )


@router.get("/{cp_id}/transactions", summary="Операции контрагента")
def get_counterparty_transactions(
    cp_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cp = _get_counterparty_or_404(cp_id, current_user.id, db)
    contract_ids = [c.id for c in db.query(models.Contract.id).filter(
        models.Contract.counterparty_id == cp.id
    ).all()]
    if not contract_ids:
        return []
    fund_ids = [f.id for f in db.query(models.Fund.id).filter(
        models.Fund.contract_id.in_(contract_ids)
    ).all()]
    if not fund_ids:
        return []
    return (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.fund_id.in_(fund_ids),
        )
        .order_by(models.Transaction.date.desc())
        .all()
    )


@router.post("", response_model=CounterpartyResponse, status_code=status.HTTP_201_CREATED,
             summary="Создать контрагента")
def create_counterparty(
    data: CounterpartyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CounterpartyResponse:
    cp = models.Counterparty(user_id=current_user.id, name=data.name, description=data.description)
    db.add(cp)
    db.flush()
    # Автосоздание договора "Основной"
    default_contract = models.Contract(counterparty_id=cp.id, name="Основной")
    db.add(default_contract)
    db.commit()
    db.refresh(cp)
    return CounterpartyResponse(
        id=cp.id,
        user_id=cp.user_id,
        name=cp.name,
        description=cp.description,
        balance=0.0,
        contracts=[ContractResponse.model_validate(c) for c in cp.contracts],
        created_at=cp.created_at,
    )


@router.put("/{cp_id}", response_model=CounterpartyResponse, summary="Обновить контрагента")
def update_counterparty(
    cp_id: int,
    data: CounterpartyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CounterpartyResponse:
    cp = _get_counterparty_or_404(cp_id, current_user.id, db)
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(cp, field, value)
    db.commit()
    db.refresh(cp)
    balances = _calc_counterparty_balances(current_user.id, db)
    return CounterpartyResponse(
        id=cp.id,
        user_id=cp.user_id,
        name=cp.name,
        description=cp.description,
        balance=balances.get(cp.id, 0.0),
        contracts=[ContractResponse.model_validate(c) for c in cp.contracts],
        created_at=cp.created_at,
    )


@router.delete("/{cp_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить контрагента")
def delete_counterparty(
    cp_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    cp = _get_counterparty_or_404(cp_id, current_user.id, db)
    # Проверяем, есть ли фонды привязанные к договорам этого контрагента
    contract_ids = [c.id for c in cp.contracts]
    if contract_ids:
        fund_count = db.query(models.Fund).filter(models.Fund.contract_id.in_(contract_ids)).count()
        if fund_count > 0:
            raise HTTPException(status_code=409, detail="Нельзя удалить: есть связанные фонды")
    db.delete(cp)
    db.commit()


# ──────────────────────────────────────────────
# Contract endpoints
# ──────────────────────────────────────────────

@router.get("/{cp_id}/contracts", response_model=list[ContractResponse],
            summary="Список договоров контрагента")
def list_contracts(
    cp_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Contract]:
    _get_counterparty_or_404(cp_id, current_user.id, db)
    return (
        db.query(models.Contract)
        .filter(models.Contract.counterparty_id == cp_id)
        .order_by(models.Contract.created_at)
        .all()
    )


@router.post("/{cp_id}/contracts", response_model=ContractResponse,
             status_code=status.HTTP_201_CREATED, summary="Создать договор")
def create_contract(
    cp_id: int,
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Contract:
    _get_counterparty_or_404(cp_id, current_user.id, db)
    contract = models.Contract(counterparty_id=cp_id, name=data.name, description=data.description)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.put("/contracts/{contract_id}", response_model=ContractResponse, summary="Обновить договор")
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Contract:
    contract = db.query(models.Contract).join(models.Counterparty).filter(
        models.Contract.id == contract_id,
        models.Counterparty.user_id == current_user.id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(contract, field, value)
    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Удалить договор")
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    contract = db.query(models.Contract).join(models.Counterparty).filter(
        models.Contract.id == contract_id,
        models.Counterparty.user_id == current_user.id,
    ).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    if contract.name == "Основной":
        raise HTTPException(status_code=409, detail="Нельзя удалить договор 'Основной'")
    fund_count = db.query(models.Fund).filter(models.Fund.contract_id == contract_id).count()
    if fund_count > 0:
        raise HTTPException(status_code=409, detail="Нельзя удалить: есть связанные фонды")
    db.delete(contract)
    db.commit()
