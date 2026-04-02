import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/attachments", tags=["attachments"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


# ──────────────────────────────────────────────
# Схемы Pydantic
# ──────────────────────────────────────────────

class AttachmentResponse(BaseModel):
    id: int
    user_id: int
    entity_type: models.AttachmentEntityType
    entity_id: int
    filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_max_size(user_id: int, db: Session) -> int:
    setting = db.query(models.AppSetting).filter(models.AppSetting.user_id == user_id).first()
    max_mb = setting.max_attachment_size_mb if setting else 10
    return max_mb * 1024 * 1024


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED,
             summary="Загрузить файл")
async def upload_attachment(
    entity_type: models.AttachmentEntityType = Form(...),
    entity_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Attachment:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Допустимые форматы: PDF, JPEG, PNG")

    max_size = _get_max_size(current_user.id, db)
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail=f"Файл превышает лимит {max_size // (1024*1024)} МБ")

    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    user_dir = os.path.join(UPLOAD_DIR, str(current_user.id), entity_type.value)
    os.makedirs(user_dir, exist_ok=True)
    filepath = os.path.join(user_dir, unique_name)

    with open(filepath, "wb") as f:
        f.write(contents)

    attachment = models.Attachment(
        user_id=current_user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        filename=file.filename or "file",
        filepath=filepath,
        mime_type=file.content_type,
        size_bytes=len(contents),
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("", response_model=list[AttachmentResponse], summary="Список вложений")
def list_attachments(
    entity_type: models.AttachmentEntityType,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Attachment]:
    return (
        db.query(models.Attachment)
        .filter(
            models.Attachment.user_id == current_user.id,
            models.Attachment.entity_type == entity_type,
            models.Attachment.entity_id == entity_id,
        )
        .order_by(models.Attachment.created_at)
        .all()
    )


@router.get("/{attachment_id}/download", summary="Скачать файл")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    att = db.query(models.Attachment).filter(
        models.Attachment.id == attachment_id,
        models.Attachment.user_id == current_user.id,
    ).first()
    if not att:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    if not os.path.exists(att.filepath):
        raise HTTPException(status_code=404, detail="Файл не найден на диске")
    return FileResponse(att.filepath, filename=att.filename, media_type=att.mime_type)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить вложение")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    att = db.query(models.Attachment).filter(
        models.Attachment.id == attachment_id,
        models.Attachment.user_id == current_user.id,
    ).first()
    if not att:
        raise HTTPException(status_code=404, detail="Вложение не найдено")
    if os.path.exists(att.filepath):
        os.remove(att.filepath)
    db.delete(att)
    db.commit()
