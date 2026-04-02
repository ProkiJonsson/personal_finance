from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/categories", tags=["categories"])


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class CategoryCreate(BaseModel):
    """Тело запроса для создания категории"""
    name: str
    type: Optional[models.CategoryType] = None
    level: int = 1
    parent_id: Optional[int] = None
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название категории не может быть пустым")
        return v

    @field_validator("level")
    @classmethod
    def level_in_range(cls, v: int) -> int:
        if not (1 <= v <= 4):
            raise ValueError("Уровень категории должен быть от 1 до 4")
        return v

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "CategoryCreate":
        """
        Схема уровней: 4=Виды деятельности (корень), 3=Тип операции, 2=Группа статей, 1=Статья.
        Уровень 4 — корневой, не имеет родителя.
        Уровень 3 — родитель необязателен (если есть, должен быть уровня 4).
        Уровень 2 — родитель необязателен (если есть, должен быть уровня 3).
        Уровень 1 — родитель необязателен (если есть, должен быть уровня 2).
        """
        if self.level == 4 and self.parent_id is not None:
            raise ValueError("Вид деятельности (уровень 4) не может иметь родителя")
        return self


class CategoryUpdate(BaseModel):
    """Тело запроса для обновления категории — все поля опциональны"""
    name: Optional[str] = None
    type: Optional[models.CategoryType] = None
    sort_order: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Название категории не может быть пустым")
        return v


class CategoryMove(BaseModel):
    """Тело запроса для перемещения категории по иерархии"""
    level: int
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None

    @field_validator("level")
    @classmethod
    def level_in_range(cls, v: int) -> int:
        if not (1 <= v <= 4):
            raise ValueError("Уровень категории должен быть от 1 до 4")
        return v


class CategoryResponse(BaseModel):
    """Ответ с данными категории"""
    id: int
    user_id: str
    name: str
    type: Optional[models.CategoryType]
    level: int
    parent_id: Optional[int]
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────

def _get_category_or_404(category_id: int, user_id: str, db: Session) -> models.Category:
    """Возвращает категорию пользователя или выбрасывает 404."""
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == user_id,
    ).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Категория не найдена")
    return category


def _verify_parent(parent_id: int, user_id: str, expected_child_level: int, db: Session) -> None:
    """
    Проверяет, что родительская категория существует, принадлежит пользователю
    и её уровень на единицу выше уровня дочерней (родитель имеет больший номер уровня).
    Схема: 4 → 3 → 2.
    """
    parent = db.query(models.Category).filter(
        models.Category.id == parent_id,
        models.Category.user_id == user_id,
    ).first()
    if not parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Родительская категория не найдена")
    if parent.level != expected_child_level + 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Родительская категория должна быть уровня {expected_child_level + 1}",
        )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("", response_model=list[CategoryResponse], summary="Список категорий текущего пользователя")
def list_categories(
    type: Optional[models.CategoryType] = None,
    parent_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Category]:
    """
    Возвращает категории пользователя.
    Фильтры (опциональные): type (income/expense), parent_id.
    Сортировка: level → sort_order → name.
    """
    query = db.query(models.Category).filter(models.Category.user_id == current_user.id)

    if type is not None:
        query = query.filter(models.Category.type == type)
    if parent_id is not None:
        query = query.filter(models.Category.parent_id == parent_id)

    return query.order_by(
        models.Category.level,
        models.Category.sort_order,
        models.Category.name,
    ).all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Создать категорию")
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Category:
    # Проверяем родительскую категорию, если указана
    if data.parent_id is not None:
        _verify_parent(data.parent_id, current_user.id, data.level, db)

    # exclude_none=True: не передаём None в конструктор SQLAlchemy-модели.
    # SQLAlchemy's Enum тип при flush валидирует значение — передача None
    # через **kwargs вызывает ошибку даже для nullable-колонки.
    # Nullable-поля (type, parent_id) без значения SQLAlchemy сам выставит в NULL.
    category = models.Category(
        user_id=current_user.id,
        **data.model_dump(exclude_none=True),
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse, summary="Обновить категорию")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Category:
    # level и parent_id намеренно не обновляются —
    # перемещение категории по иерархии требует отдельной логики
    category = _get_category_or_404(category_id, current_user.id, db)

    updates = data.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}/move", response_model=CategoryResponse, summary="Переместить категорию по иерархии")
def move_category(
    category_id: int,
    data: CategoryMove,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Category:
    category = _get_category_or_404(category_id, current_user.id, db)

    if data.level == 4 and data.parent_id is not None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Вид деятельности (уровень 4) не может иметь родителя")
    if data.parent_id is not None:
        _verify_parent(data.parent_id, current_user.id, data.level, db)

    level_delta = data.level - category.level
    category.level = data.level
    category.parent_id = data.parent_id
    if data.sort_order is not None:
        category.sort_order = data.sort_order

    if level_delta != 0:
        def update_children(parent_id: int, delta: int) -> None:
            children = db.query(models.Category).filter(
                models.Category.parent_id == parent_id,
                models.Category.user_id == current_user.id,
            ).all()
            for child in children:
                child.level += delta
                update_children(child.id, delta)
        update_children(category_id, level_delta)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/clear-user-data", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить все статьи и группы пользователя")
def clear_user_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    """Удаляет все категории уровней 1 и 2 текущего пользователя (при смене режима учёта)."""
    for level in [1, 2]:
        db.query(models.Category).filter(
            models.Category.user_id == current_user.id,
            models.Category.level == level,
        ).delete(synchronize_session=False)
    db.commit()


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить категорию")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    category = _get_category_or_404(category_id, current_user.id, db)

    # Нельзя удалить категорию, у которой есть дочерние
    children_count = db.query(models.Category).filter(
        models.Category.parent_id == category_id
    ).count()
    if children_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить категорию, у которой есть подкатегории",
        )

    db.delete(category)
    db.commit()
