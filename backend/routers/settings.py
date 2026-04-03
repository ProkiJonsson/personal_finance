from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/settings", tags=["settings"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class AppSettingResponse(BaseModel):
    fund_accounting_enabled: bool

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    fund_accounting_enabled: Optional[bool] = None


class TaxBracketSchema(BaseModel):
    threshold_amount: float
    rate: float


class TaxSettingCreate(BaseModel):
    year: int
    tax_free_threshold: float
    brackets: list[TaxBracketSchema] = [
        TaxBracketSchema(threshold_amount=2400000, rate=0.13),
        TaxBracketSchema(threshold_amount=50000000, rate=0.15),
    ]


class TaxBracketResponse(BaseModel):
    id: int
    threshold_amount: float
    rate: float
    sort_order: int

    model_config = {"from_attributes": True}


class TaxSettingResponse(BaseModel):
    id: int
    user_id: str
    year: int
    tax_free_threshold: float
    brackets: list[TaxBracketResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# App Settings
# ──────────────────────────────────────────────

def _get_or_create_app_setting(user_id: str, db: Session) -> models.AppSetting:
    setting = db.query(models.AppSetting).filter(models.AppSetting.user_id == user_id).first()
    if not setting:
        setting = models.AppSetting(user_id=user_id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


@router.get("", response_model=AppSettingResponse, summary="Получить настройки")
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.AppSetting:
    return _get_or_create_app_setting(current_user.id, db)


@router.put("", response_model=AppSettingResponse, summary="Обновить настройки")
def update_settings(
    data: AppSettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.AppSetting:
    setting = _get_or_create_app_setting(current_user.id, db)
    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(setting, field, value)
    db.commit()
    db.refresh(setting)
    return setting


# ──────────────────────────────────────────────
# Tax Settings (НДФЛ на вклады)
# ──────────────────────────────────────────────

@router.get("/tax", response_model=list[TaxSettingResponse], summary="НДФЛ по годам")
def list_tax_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.TaxSetting]:
    return (
        db.query(models.TaxSetting)
        .filter(models.TaxSetting.user_id == current_user.id)
        .order_by(models.TaxSetting.year.desc())
        .all()
    )


@router.post("/tax", response_model=TaxSettingResponse, status_code=status.HTTP_201_CREATED,
             summary="Создать/обновить НДФЛ для года")
def upsert_tax_setting(
    data: TaxSettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.TaxSetting:
    if len(data.brackets) > 5:
        raise HTTPException(status_code=400, detail="Максимум 5 порогов")
    if len(data.brackets) < 1:
        raise HTTPException(status_code=400, detail="Нужен хотя бы один порог")

    existing = db.query(models.TaxSetting).filter(
        models.TaxSetting.user_id == current_user.id,
        models.TaxSetting.year == data.year,
    ).first()
    if existing:
        existing.tax_free_threshold = data.tax_free_threshold
        # Заменяем brackets
        existing.brackets.clear()
        db.flush()
        for i, b in enumerate(data.brackets):
            existing.brackets.append(models.TaxBracket(
                threshold_amount=b.threshold_amount, rate=b.rate, sort_order=i,
            ))
        db.commit()
        db.refresh(existing)
        return existing
    ts = models.TaxSetting(user_id=current_user.id, year=data.year, tax_free_threshold=data.tax_free_threshold)
    for i, b in enumerate(data.brackets):
        ts.brackets.append(models.TaxBracket(
            threshold_amount=b.threshold_amount, rate=b.rate, sort_order=i,
        ))
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return ts


@router.delete("/tax/{year}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить НДФЛ для года")
def delete_tax_setting(
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    ts = db.query(models.TaxSetting).filter(
        models.TaxSetting.user_id == current_user.id,
        models.TaxSetting.year == year,
    ).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Настройка НДФЛ не найдена")
    db.delete(ts)
    db.commit()
