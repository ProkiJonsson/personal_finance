from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/cascades", tags=["cascades"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class SlotData(BaseModel):
    fund_id: int
    target_amount: float
    sort_order: int

    @field_validator("target_amount")
    @classmethod
    def target_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Целевая сумма не может быть отрицательной")
        return v


class SplitRuleData(BaseModel):
    trigger_position: Optional[int] = None  # NULL, 0..N, -1
    target_fund_id: int
    percentage: float

    @field_validator("percentage")
    @classmethod
    def pct_valid(cls, v: float) -> float:
        if v <= 0 or v > 1:
            raise ValueError("Процент должен быть от 0 до 1 (напр. 0.10 = 10%)")
        return v


class CascadeCreate(BaseModel):
    effective_from: date
    slots: list[SlotData]
    split_rules: list[SplitRuleData] = []


class CascadeUpdate(BaseModel):
    effective_from: Optional[date] = None
    slots: Optional[list[SlotData]] = None
    split_rules: Optional[list[SplitRuleData]] = None


class SlotResponse(BaseModel):
    id: int
    fund_id: int
    fund_name: str
    target_amount: float
    sort_order: int

    model_config = {"from_attributes": True}


class SplitRuleResponse(BaseModel):
    id: int
    trigger_position: Optional[int]
    target_fund_id: int
    target_fund_name: str
    percentage: float

    model_config = {"from_attributes": True}


class CascadeResponse(BaseModel):
    id: int
    user_id: int
    effective_from: date
    slots: list[SlotResponse]
    split_rules: list[SplitRuleResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class CascadeListItem(BaseModel):
    id: int
    effective_from: date
    slots_count: int
    rules_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _cascade_to_response(cascade: models.Cascade) -> CascadeResponse:
    slots = [
        SlotResponse(
            id=s.id,
            fund_id=s.fund_id,
            fund_name=s.fund.name if s.fund else f"Fund {s.fund_id}",
            target_amount=s.target_amount,
            sort_order=s.sort_order,
        )
        for s in sorted(cascade.slots, key=lambda x: x.sort_order)
    ]
    rules = [
        SplitRuleResponse(
            id=r.id,
            trigger_position=r.trigger_position,
            target_fund_id=r.target_fund_id,
            target_fund_name=r.target_fund.name if r.target_fund else f"Fund {r.target_fund_id}",
            percentage=r.percentage,
        )
        for r in cascade.split_rules
    ]
    return CascadeResponse(
        id=cascade.id,
        user_id=cascade.user_id,
        effective_from=cascade.effective_from,
        slots=slots,
        split_rules=rules,
        created_at=cascade.created_at,
    )


def _load_cascade(cascade_id: int, user_id: int, db: Session) -> models.Cascade:
    cascade = (
        db.query(models.Cascade)
        .options(
            joinedload(models.Cascade.slots).joinedload(models.CascadeSlot.fund),
            joinedload(models.Cascade.split_rules).joinedload(models.SplitRule.target_fund),
        )
        .filter(models.Cascade.id == cascade_id, models.Cascade.user_id == user_id)
        .first()
    )
    if not cascade:
        raise HTTPException(status_code=404, detail="Каскад не найден")
    return cascade


def _verify_funds_ownership(fund_ids: list[int], user_id: int, db: Session) -> None:
    existing = set(
        f.id for f in db.query(models.Fund.id).filter(
            models.Fund.id.in_(fund_ids),
            models.Fund.user_id == user_id,
        ).all()
    )
    missing = set(fund_ids) - existing
    if missing:
        raise HTTPException(status_code=404, detail=f"Фонды не найдены: {missing}")


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[CascadeListItem], summary="Список каскадов (история)")
def list_cascades(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[CascadeListItem]:
    cascades = (
        db.query(models.Cascade)
        .options(joinedload(models.Cascade.slots), joinedload(models.Cascade.split_rules))
        .filter(models.Cascade.user_id == current_user.id)
        .order_by(models.Cascade.effective_from.desc())
        .all()
    )
    return [
        CascadeListItem(
            id=c.id,
            effective_from=c.effective_from,
            slots_count=len(c.slots),
            rules_count=len(c.split_rules),
            created_at=c.created_at,
        )
        for c in cascades
    ]


@router.get("/active", response_model=Optional[CascadeResponse], summary="Активный каскад")
def get_active_cascade(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> Optional[CascadeResponse]:
    cascade = (
        db.query(models.Cascade)
        .options(
            joinedload(models.Cascade.slots).joinedload(models.CascadeSlot.fund),
            joinedload(models.Cascade.split_rules).joinedload(models.SplitRule.target_fund),
        )
        .filter(
            models.Cascade.user_id == current_user.id,
            models.Cascade.effective_from <= date.today(),
        )
        .order_by(models.Cascade.effective_from.desc())
        .first()
    )
    if not cascade:
        return None
    return _cascade_to_response(cascade)


@router.get("/{cascade_id}", response_model=CascadeResponse, summary="Детали каскада")
def get_cascade(
    cascade_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CascadeResponse:
    cascade = _load_cascade(cascade_id, current_user.id, db)
    return _cascade_to_response(cascade)


@router.post("", response_model=CascadeResponse, status_code=status.HTTP_201_CREATED,
             summary="Создать каскад")
def create_cascade(
    data: CascadeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CascadeResponse:
    all_fund_ids = [s.fund_id for s in data.slots] + [r.target_fund_id for r in data.split_rules]
    _verify_funds_ownership(all_fund_ids, current_user.id, db)

    cascade = models.Cascade(user_id=current_user.id, effective_from=data.effective_from)
    db.add(cascade)
    db.flush()

    for s in data.slots:
        db.add(models.CascadeSlot(
            cascade_id=cascade.id, fund_id=s.fund_id,
            target_amount=s.target_amount, sort_order=s.sort_order,
        ))
    for r in data.split_rules:
        db.add(models.SplitRule(
            cascade_id=cascade.id, trigger_position=r.trigger_position,
            target_fund_id=r.target_fund_id, percentage=r.percentage,
        ))

    db.commit()
    return _cascade_to_response(_load_cascade(cascade.id, current_user.id, db))


@router.put("/{cascade_id}", response_model=CascadeResponse, summary="Обновить каскад")
def update_cascade(
    cascade_id: int,
    data: CascadeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CascadeResponse:
    cascade = _load_cascade(cascade_id, current_user.id, db)

    # Нельзя редактировать если есть более новый каскад
    newer = db.query(models.Cascade).filter(
        models.Cascade.user_id == current_user.id,
        models.Cascade.effective_from > cascade.effective_from,
    ).first()
    if newer:
        raise HTTPException(status_code=409, detail="Нельзя редактировать: есть более новый каскад")

    if data.effective_from is not None:
        cascade.effective_from = data.effective_from

    if data.slots is not None:
        fund_ids = [s.fund_id for s in data.slots]
        _verify_funds_ownership(fund_ids, current_user.id, db)
        # Удаляем старые slots и создаём новые
        for old_slot in cascade.slots:
            db.delete(old_slot)
        db.flush()
        for s in data.slots:
            db.add(models.CascadeSlot(
                cascade_id=cascade.id, fund_id=s.fund_id,
                target_amount=s.target_amount, sort_order=s.sort_order,
            ))

    if data.split_rules is not None:
        fund_ids = [r.target_fund_id for r in data.split_rules]
        _verify_funds_ownership(fund_ids, current_user.id, db)
        for old_rule in cascade.split_rules:
            db.delete(old_rule)
        db.flush()
        for r in data.split_rules:
            db.add(models.SplitRule(
                cascade_id=cascade.id, trigger_position=r.trigger_position,
                target_fund_id=r.target_fund_id, percentage=r.percentage,
            ))

    db.commit()
    return _cascade_to_response(_load_cascade(cascade.id, current_user.id, db))


@router.delete("/{cascade_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить каскад")
def delete_cascade(
    cascade_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    cascade = _load_cascade(cascade_id, current_user.id, db)
    # Можно удалить только последний каскад
    latest = (
        db.query(models.Cascade)
        .filter(models.Cascade.user_id == current_user.id)
        .order_by(models.Cascade.effective_from.desc())
        .first()
    )
    if latest and latest.id != cascade.id:
        raise HTTPException(status_code=409, detail="Можно удалить только последний каскад")
    db.delete(cascade)
    db.commit()


@router.post("/{cascade_id}/copy", response_model=CascadeResponse,
             status_code=status.HTTP_201_CREATED, summary="Копировать каскад")
def copy_cascade(
    cascade_id: int,
    effective_from: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> CascadeResponse:
    source = _load_cascade(cascade_id, current_user.id, db)

    new_cascade = models.Cascade(user_id=current_user.id, effective_from=effective_from)
    db.add(new_cascade)
    db.flush()

    for s in source.slots:
        db.add(models.CascadeSlot(
            cascade_id=new_cascade.id, fund_id=s.fund_id,
            target_amount=s.target_amount, sort_order=s.sort_order,
        ))
    for r in source.split_rules:
        db.add(models.SplitRule(
            cascade_id=new_cascade.id, trigger_position=r.trigger_position,
            target_fund_id=r.target_fund_id, percentage=r.percentage,
        ))

    db.commit()
    return _cascade_to_response(_load_cascade(new_cascade.id, current_user.id, db))
