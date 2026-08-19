from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user import User
from app.services import uploads

router = APIRouter(prefix="/uploads", tags=["uploads"])


class PresignRequest(BaseModel):
    purpose: Literal["checkin", "avatar"]
    content_type: Literal["image/jpeg", "image/png", "image/heic", "image/webp"]


class PresignResponse(BaseModel):
    upload_url: str
    public_url: str


@router.post("/presign", response_model=PresignResponse)
def presign_upload(
    body: PresignRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        return uploads.create_presigned_upload(
            current_user.id, body.purpose, body.content_type
        )
    except uploads.StorageNotConfiguredError:
        raise HTTPException(status_code=503, detail="Photo storage not configured")
