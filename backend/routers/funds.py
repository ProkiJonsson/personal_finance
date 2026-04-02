from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import case, func, extract
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/funds", tags=["funds"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class FundCreate(BaseModel):
    name: str
    type: models.FundType
    contract_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название фонда не может быть пустым")
        return v


class FundUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[models.FundType] = None
    contract_id: Optional[int] = None
    is_archived: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Название фонда не может быть пустым")
        return v


class FundResponse(BaseModel):
    id: int
    user_id: int
    name: str
    type: models.FundType
    balance: float
    contract_id: Optional[int]
    counterparty_name: Optional[str]
    contract_name: Optional[str]
    is_archived: bool
    is_system: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReorderItem(BaseModel):
    fund_id: int
    sort_order: int


class DistributeRequest(BaseModel):
    amount: float
    month: Optional[str] = None  # YYYY-MM, по умолчанию текущий
    is_deposit_income: bool = False

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Сумма должна быть положительной")
        return v


class AllocationItem(BaseModel):
    fund_id: int
    fund_name: str
    current_month_income: float
    target_amount: float
    allocated: float
    source: str = "cascade"


class TaxDeduction(BaseModel):
    fund_id: int
    fund_name: str
    amount: float
    ytd_deposit_income: float
    tax_rate_applied: str


class DistributeResponse(BaseModel):
    tax_deduction: Optional[TaxDeduction] = None
    items: list[AllocationItem]
    investment_items: list[AllocationItem]
    total_distributed: float


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def _get_fund_or_404(fund_id: int, user_id: int, db: Session) -> models.Fund:
    fund = db.query(models.Fund).filter(
        models.Fund.id == fund_id,
        models.Fund.user_id == user_id,
    ).first()
    if not fund:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Фонд не найден")
    return fund


def _calc_balances(user_id: int, db: Session) -> dict[int, float]:
    rows = (
        db.query(
            models.Transaction.fund_id,
            func.coalesce(
                func.sum(
                    case(
                        (models.Transaction.type == models.TransactionType.income, models.Transaction.amount),
                        else_=0.0,
                    )
                ), 0.0,
            ).label("income"),
            func.coalesce(
                func.sum(
                    case(
                        (models.Transaction.type == models.TransactionType.expense, models.Transaction.amount),
                        else_=0.0,
                    )
                ), 0.0,
            ).label("expense"),
        )
        .filter(models.Transaction.user_id == user_id)
        .group_by(models.Transaction.fund_id)
        .all()
    )
    return {row.fund_id: row.income - row.expense for row in rows}


def _fund_to_response(fund: models.Fund, balances: dict[int, float]) -> FundResponse:
    counterparty_name = None
    contract_name = None
    if fund.contract:
        contract_name = fund.contract.name
        if fund.contract.counterparty:
            counterparty_name = fund.contract.counterparty.name
    return FundResponse(
        id=fund.id,
        user_id=fund.user_id,
        name=fund.name,
        type=fund.type,
        balance=balances.get(fund.id, 0.0),
        contract_id=fund.contract_id,
        counterparty_name=counterparty_name,
        contract_name=contract_name,
        is_archived=fund.is_archived,
        is_system=fund.is_system,
        created_at=fund.created_at,
    )


def _get_month_income(user_id: int, fund_id: int, year: int, month: int, db: Session) -> float:
    result = (
        db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0))
        .filter(
            models.Transaction.user_id == user_id,
            models.Transaction.fund_id == fund_id,
            models.Transaction.type == models.TransactionType.income,
            extract("year", models.Transaction.date) == year,
            extract("month", models.Transaction.date) == month,
        )
        .scalar()
    )
    return float(result)


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[FundResponse], summary="Список фондов")
def list_funds(
    type: Optional[models.FundType] = None,
    archived: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[FundResponse]:
    query = (
        db.query(models.Fund)
        .options(joinedload(models.Fund.contract).joinedload(models.Contract.counterparty))
        .filter(models.Fund.user_id == current_user.id)
    )
    if type is not None:
        query = query.filter(models.Fund.type == type)
    if archived is not None:
        query = query.filter(models.Fund.is_archived == archived)
    funds = query.order_by(models.Fund.created_at).all()
    balances = _calc_balances(current_user.id, db)
    return [_fund_to_response(f, balances) for f in funds]


@router.post("", response_model=FundResponse, status_code=status.HTTP_201_CREATED, summary="Создать фонд")
def create_fund(
    data: FundCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> FundResponse:
    if data.contract_id is not None:
        contract = db.query(models.Contract).join(models.Counterparty).filter(
            models.Contract.id == data.contract_id,
            models.Counterparty.user_id == current_user.id,
        ).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")

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

    if "contract_id" in updates and updates["contract_id"] is not None:
        contract = db.query(models.Contract).join(models.Counterparty).filter(
            models.Contract.id == updates["contract_id"],
            models.Counterparty.user_id == current_user.id,
        ).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")

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
    if fund.is_system:
        raise HTTPException(status_code=409, detail="Нельзя удалить системный фонд")
    # Явная проверка связанных транзакций (надёжнее чем ловить IntegrityError)
    tx_count = db.query(models.Transaction).filter(models.Transaction.fund_id == fund_id).count()
    if tx_count > 0:
        raise HTTPException(status_code=409, detail="Нельзя удалить фонд: есть связанные операции")
    try:
        db.delete(fund)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Нельзя удалить фонд: есть связанные данные")


# ──────────────────────────────────────────────
# Distribute — полуавтомат распределения дохода
# ──────────────────────────────────────────────

@router.post("/distribute", response_model=DistributeResponse, summary="Рассчитать распределение дохода")
def distribute_income(
    data: DistributeRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> DistributeResponse:
    today = date.today()
    if data.month:
        parts = data.month.split("-")
        target_year, target_month = int(parts[0]), int(parts[1])
    else:
        target_year, target_month = today.year, today.month

    amount = data.amount
    tax_deduction = None
    items: list[AllocationItem] = []
    investment_items: list[AllocationItem] = []

    # 1. НДФЛ на вклады
    if data.is_deposit_income:
        tax_deduction = _calc_tax_deduction(current_user.id, amount, target_year, db)
        if tax_deduction:
            amount -= tax_deduction.amount

    # 2. Получить активный каскад
    cascade = (
        db.query(models.Cascade)
        .filter(
            models.Cascade.user_id == current_user.id,
            models.Cascade.effective_from <= today,
        )
        .order_by(models.Cascade.effective_from.desc())
        .first()
    )
    if not cascade:
        # Нет каскада — всё в один allocation item
        return DistributeResponse(
            tax_deduction=tax_deduction,
            items=[],
            investment_items=[],
            total_distributed=data.amount,
        )

    slots = cascade.slots  # уже отсортированы по sort_order
    split_rules = cascade.split_rules

    # Индексируем правила по trigger_position
    rules_by_pos: dict[Optional[int], list[models.SplitRule]] = {}
    for rule in split_rules:
        rules_by_pos.setdefault(rule.trigger_position, []).append(rule)

    remaining = amount

    # Правила от каждого рубля (trigger_position = NULL)
    global_rules = rules_by_pos.get(None, [])
    if global_rules:
        for rule in global_rules:
            split_amount = round(remaining * rule.percentage, 2)
            fund = db.get(models.Fund, rule.target_fund_id)
            if fund:
                investment_items.append(AllocationItem(
                    fund_id=fund.id,
                    fund_name=fund.name,
                    current_month_income=_get_month_income(current_user.id, fund.id, target_year, target_month, db),
                    target_amount=0,
                    allocated=split_amount,
                    source=f"split {int(rule.percentage*100)}% от каждого рубля",
                ))
                remaining -= split_amount

    # 3. Каскад по позициям
    for slot in slots:
        if remaining <= 0:
            break
        current_income = _get_month_income(current_user.id, slot.fund_id, target_year, target_month, db)
        need = max(0, slot.target_amount - current_income)
        allocated = min(remaining, need)

        items.append(AllocationItem(
            fund_id=slot.fund_id,
            fund_name=slot.fund.name if slot.fund else f"Fund {slot.fund_id}",
            current_month_income=current_income,
            target_amount=slot.target_amount,
            allocated=allocated,
        ))
        remaining -= allocated

        # Правила после этой позиции
        if remaining > 0 and slot.sort_order in rules_by_pos:
            for rule in rules_by_pos[slot.sort_order]:
                split_amount = round(remaining * rule.percentage, 2)
                fund = db.get(models.Fund, rule.target_fund_id)
                if fund:
                    investment_items.append(AllocationItem(
                        fund_id=fund.id,
                        fund_name=fund.name,
                        current_month_income=_get_month_income(current_user.id, fund.id, target_year, target_month, db),
                        target_amount=0,
                        allocated=split_amount,
                        source=f"split {int(rule.percentage*100)}% после поз.{slot.sort_order}",
                    ))
                    remaining -= split_amount

    # 4. Правила после всех позиций (trigger_position = -1)
    if remaining > 0 and -1 in rules_by_pos:
        for rule in rules_by_pos[-1]:
            split_amount = round(remaining * rule.percentage, 2)
            fund = db.get(models.Fund, rule.target_fund_id)
            if fund:
                investment_items.append(AllocationItem(
                    fund_id=fund.id,
                    fund_name=fund.name,
                    current_month_income=_get_month_income(current_user.id, fund.id, target_year, target_month, db),
                    target_amount=0,
                    allocated=split_amount,
                    source=f"split {int(rule.percentage*100)}% после всех",
                ))
                remaining -= split_amount

    return DistributeResponse(
        tax_deduction=tax_deduction,
        items=items,
        investment_items=investment_items,
        total_distributed=data.amount,
    )


def _calc_tax_deduction(user_id: int, amount: float, year: int, db: Session) -> Optional[TaxDeduction]:
    """Прогрессивный расчёт НДФЛ на доход от вкладов."""
    tax_setting = (
        db.query(models.TaxSetting)
        .filter(models.TaxSetting.user_id == user_id, models.TaxSetting.year <= year)
        .order_by(models.TaxSetting.year.desc())
        .first()
    )
    if not tax_setting:
        return None

    # Находим системный фонд "Налоги на вклады"
    tax_fund = db.query(models.Fund).filter(
        models.Fund.user_id == user_id,
        models.Fund.type == models.FundType.tax_reserve,
        models.Fund.is_system == True,
    ).first()
    if not tax_fund:
        # Автосоздание системного фонда
        tax_fund = models.Fund(
            user_id=user_id, name="Налоги на вклады",
            type=models.FundType.tax_reserve, is_system=True,
        )
        db.add(tax_fund)
        db.flush()

    # YTD доход от вкладов (сумма income-транзакций с is_deposit_income — определяем по фондам placement)
    placement_fund_ids = [f.id for f in db.query(models.Fund.id).filter(
        models.Fund.user_id == user_id,
        models.Fund.type == models.FundType.placement,
    ).all()]

    ytd_income = 0.0
    if placement_fund_ids:
        ytd_income = float(db.query(func.coalesce(func.sum(models.Transaction.amount), 0.0)).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.fund_id.in_(placement_fund_ids),
            models.Transaction.type == models.TransactionType.income,
            extract("year", models.Transaction.date) == year,
        ).scalar())

    # Рассчитываем прогрессивный налог
    threshold = tax_setting.tax_free_threshold
    elevated = tax_setting.elevated_threshold
    prev_total = ytd_income
    new_total = ytd_income + amount

    tax = 0.0
    rate_desc = "0%"

    # Часть в зоне 0%
    if new_total <= threshold:
        tax = 0.0
        rate_desc = "0%"
    else:
        # Часть до порога — 0%
        taxable_start = max(prev_total, threshold)
        # Часть в зоне 13%
        if taxable_start < elevated:
            taxable_13 = min(new_total, elevated) - taxable_start
            if taxable_13 > 0:
                tax += taxable_13 * tax_setting.rate_standard
                rate_desc = f"{int(tax_setting.rate_standard*100)}%"
        # Часть в зоне 15%
        if new_total > elevated:
            taxable_15_start = max(taxable_start, elevated)
            taxable_15 = new_total - taxable_15_start
            if taxable_15 > 0:
                tax += taxable_15 * tax_setting.rate_elevated
                rate_desc = f"{int(tax_setting.rate_elevated*100)}%"

    tax = round(tax, 2)
    if tax <= 0:
        return None

    return TaxDeduction(
        fund_id=tax_fund.id,
        fund_name=tax_fund.name,
        amount=tax,
        ytd_deposit_income=ytd_income,
        tax_rate_applied=rate_desc,
    )
