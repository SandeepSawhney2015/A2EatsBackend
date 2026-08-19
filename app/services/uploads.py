import uuid
from functools import lru_cache

import boto3

from app.core.config import get_settings

# The app never uploads through our API. It asks us for a presigned URL (a
# short-lived signed permission slip for one specific object key), PUTs the
# photo straight to the bucket, then sends the public URL back in a check-in
# or profile-picture request.

PRESIGN_EXPIRE_SECONDS = 15 * 60

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/webp": "webp",
}


class StorageNotConfiguredError(Exception):
    pass


@lru_cache
def _client():
    settings = get_settings()
    kwargs = {"region_name": settings.s3_region}
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("s3", **kwargs)


def create_presigned_upload(user_id: int, purpose: str, content_type: str) -> dict:
    """Returns {upload_url, public_url}. The client PUTs the file bytes to
    upload_url (with the same Content-Type header), then uses public_url."""
    settings = get_settings()
    if not settings.s3_bucket:
        raise StorageNotConfiguredError

    ext = ALLOWED_CONTENT_TYPES[content_type]
    key = f"{purpose}/{user_id}/{uuid.uuid4().hex}.{ext}"

    upload_url = _client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=PRESIGN_EXPIRE_SECONDS,
    )

    base = settings.s3_public_base_url.rstrip("/") or (
        f"https://{settings.s3_bucket}.s3.{settings.s3_region}.amazonaws.com"
    )
    return {"upload_url": upload_url, "public_url": f"{base}/{key}"}
