import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, get_admin_user
from database import get_db
import models

router = APIRouter(prefix="/admin", tags=["admin"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "admin")
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class AdminSettingResponse(BaseModel):
    max_attachment_size_mb: int


class AdminSettingUpdate(BaseModel):
    max_attachment_size_mb: Optional[int] = None


class PageContentItem(BaseModel):
    element_key: str
    content: str


class PageContentUpdate(BaseModel):
    page_key: str
    items: list[PageContentItem]


class ImageUploadResponse(BaseModel):
    url: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


# ──────────────────────────────────────────────
# Seed-данные по умолчанию
# ──────────────────────────────────────────────

DEFAULT_PAGE_CONTENT: dict[str, dict[str, str]] = {
    "dashboard": {
        "tab_title": "Личные финансы — Главная",
        "header": "Главная",
    },
    "operations": {
        "tab_title": "Личные финансы — Операции",
        "header": "Операции",
    },
    "funds": {
        "tab_title": "Личные финансы — Фонды",
        "header": "Фонды",
        "help_tip": '<strong>Что такое фонд?</strong> Фонд — это виртуальный кошелёк. Каждый рубль дохода попадает в конкретный фонд и тратится только на его цели. Настройте <a href="cascade.html">Каскад Фондов</a> чтобы автоматически распределять доход.<br><br><strong>Предопределённые типы:</strong> <strong>Бюджетные</strong> — для текущих расходов с каскадным наполнением. <strong>Инвестиционные</strong> — накопления. <strong>Налоговые резервы</strong> — откладывание на налоги. <strong>Долги</strong> — учёт кому я должен. <strong>Займы</strong> — кто должен мне. <strong>Размещения</strong> — где физически лежат инвестиции (вклады, брокер).',
        "form_hint_contract": "Привяжите к контрагенту через договор",
    },
    "accounts": {
        "tab_title": "Личные финансы — Счета",
        "header": "Счета",
        "form_hint_bank": "Можете указать банк или тип счёта",
    },
    "cascade": {
        "tab_title": "Личные финансы — Каскад Фондов",
        "header": "Каскад Фондов",
        "help_tip": '<strong>Каскад Фондов</strong> — это правила автоматического распределения дохода. Доход заполняет фонды последовательно, как стаканы:'
                    '<div style="display:flex;gap:6px;margin:12px 0;align-items:flex-end">'
                    '<div style="width:60px;height:60px;background:var(--primary);border-radius:6px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px;font-weight:700">100%</div>'
                    '<div style="width:60px;height:45px;background:var(--primary);opacity:0.7;border-radius:6px;display:flex;align-items:flex-end;justify-content:center;color:#fff;font-size:10px;font-weight:700;padding-bottom:4px"><div style="position:absolute;width:60px;height:30px;background:var(--primary);border-radius:0 0 6px 6px"></div>60%</div>'
                    '<div style="width:60px;height:30px;border:2px dashed var(--border);border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;color:var(--text-muted)">0%</div>'
                    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--text-muted)" stroke-width="2" style="flex-shrink:0"><path d="M5 12h14M12 5l7 7-7 7"/></svg>'
                    '<div style="font-size:11px;color:var(--text-muted);max-width:120px">Каждый следующий наполняется после предыдущего</div>'
                    '</div>'
                    'Настройте правила отщепления (например, 10% в инвестиции после заполнения первого фонда). Каскад действует с указанной даты до создания нового.',
    },
    "counterparties": {
        "tab_title": "Личные финансы — Контрагенты",
        "header": "Контрагенты",
        "help_tip": '<strong>Контрагенты</strong> — это банки, люди или организации, с которыми вы имеете финансовые отношения: вклады, долги, займы. У каждого контрагента может быть несколько <strong>договоров</strong> (например, два вклада в одном банке). К договорам можно прикреплять документы.',
    },
    "categories": {
        "tab_title": "Личные финансы — Статьи учёта",
        "header": "Статьи учёта",
        "activity_hint": 'Вы можете включить учёт по видам деятельности в <a href="settings.html">Настройках</a>',
    },
    "settings": {
        "tab_title": "Личные финансы — Настройки",
        "header": "Настройки",
    },
}


def seed_page_content(db: Session) -> None:
    """Заполняет page_content дефолтными значениями, если таблица пуста."""
    count = db.query(models.PageContent).count()
    if count > 0:
        return
    for page_key, elements in DEFAULT_PAGE_CONTENT.items():
        for element_key, content in elements.items():
            db.add(models.PageContent(page_key=page_key, element_key=element_key, content=content))
    db.commit()


def seed_admin_settings(db: Session) -> None:
    """Создаёт дефолтные глобальные настройки, если их нет."""
    existing = db.query(models.AdminSetting).filter(models.AdminSetting.key == "max_attachment_size_mb").first()
    if not existing:
        db.add(models.AdminSetting(key="max_attachment_size_mb", value="10"))
        db.commit()


# ──────────────────────────────────────────────
# Page Content
# ──────────────────────────────────────────────

@router.get("/page-content", summary="Контент страниц (публичный)")
def get_page_content(db: Session = Depends(get_db)) -> dict:
    rows = db.query(models.PageContent).all()
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        result.setdefault(row.page_key, {})[row.element_key] = row.content
    return result


@router.put("/page-content", summary="Обновить контент страниц")
def update_page_content(
    data: PageContentUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
) -> dict:
    for item in data.items:
        existing = db.query(models.PageContent).filter(
            models.PageContent.page_key == data.page_key,
            models.PageContent.element_key == item.element_key,
        ).first()
        if existing:
            existing.content = item.content
        else:
            db.add(models.PageContent(
                page_key=data.page_key,
                element_key=item.element_key,
                content=item.content,
            ))
    db.commit()
    return {"status": "ok"}


# ──────────────────────────────────────────────
# Admin Settings
# ──────────────────────────────────────────────

@router.get("/settings", response_model=AdminSettingResponse, summary="Глобальные настройки")
def get_admin_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> AdminSettingResponse:
    setting = db.query(models.AdminSetting).filter(models.AdminSetting.key == "max_attachment_size_mb").first()
    max_mb = int(setting.value) if setting else 10
    return AdminSettingResponse(max_attachment_size_mb=max_mb)


@router.put("/settings", response_model=AdminSettingResponse, summary="Обновить глобальные настройки")
def update_admin_settings(
    data: AdminSettingUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
) -> AdminSettingResponse:
    if data.max_attachment_size_mb is not None:
        setting = db.query(models.AdminSetting).filter(models.AdminSetting.key == "max_attachment_size_mb").first()
        if setting:
            setting.value = str(data.max_attachment_size_mb)
        else:
            db.add(models.AdminSetting(key="max_attachment_size_mb", value=str(data.max_attachment_size_mb)))
        db.commit()
    setting = db.query(models.AdminSetting).filter(models.AdminSetting.key == "max_attachment_size_mb").first()
    max_mb = int(setting.value) if setting else 10
    return AdminSettingResponse(max_attachment_size_mb=max_mb)


# ──────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse], summary="Список пользователей")
def list_users(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
) -> list[models.User]:
    q = db.query(models.User)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (models.User.name.ilike(pattern)) | (models.User.email.ilike(pattern))
        )
    return q.order_by(models.User.created_at.desc()).all()


@router.put("/users/{user_id}", response_model=UserResponse, summary="Обновить права пользователя")
def update_user_admin(
    user_id: str,
    data: UserAdminUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if data.is_admin is not None:
        if user.id == admin.id and not data.is_admin:
            raise HTTPException(status_code=400, detail="Нельзя снять права у самого себя")
        user.is_admin = data.is_admin
    if data.is_active is not None:
        if user.id == admin.id and not data.is_active:
            raise HTTPException(status_code=400, detail="Нельзя деактивировать самого себя")
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


# ──────────────────────────────────────────────
# Image Upload
# ──────────────────────────────────────────────

@router.post("/upload-image", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED,
             summary="Загрузить картинку для редактора")
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_admin_user),
) -> ImageUploadResponse:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Допустимые форматы: JPEG, PNG, GIF, WebP")

    contents = await file.read()
    max_size = 10 * 1024 * 1024  # 10 МБ для картинок редактора
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="Картинка превышает лимит 10 МБ")

    ext = os.path.splitext(file.filename or "image")[1] or ".png"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(UPLOAD_DIR, unique_name)

    with open(filepath, "wb") as f:
        f.write(contents)

    return ImageUploadResponse(url=f"/admin/images/{unique_name}")


@router.get("/images/{filename}", summary="Получить картинку")
def get_image(filename: str):
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Картинка не найдена")
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
    mime = mime_map.get(ext, "application/octet-stream")
    return FileResponse(filepath, media_type=mime)
