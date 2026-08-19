import os
from unittest.mock import patch

from app.core.config import get_settings
from app.services import uploads


class TestPresign:
    def test_requires_auth(self, client):
        r = client.post("/uploads/presign", json={"purpose": "avatar", "content_type": "image/jpeg"})
        assert r.status_code in (401, 403)

    def test_unconfigured_storage_is_503(self, client, auth_header):
        r = client.post(
            "/uploads/presign",
            json={"purpose": "avatar", "content_type": "image/jpeg"},
            headers=auth_header,
        )
        assert r.status_code == 503

    def test_bad_purpose_and_content_type_rejected(self, client, auth_header):
        r = client.post(
            "/uploads/presign",
            json={"purpose": "malware", "content_type": "image/jpeg"},
            headers=auth_header,
        )
        assert r.status_code == 422
        r = client.post(
            "/uploads/presign",
            json={"purpose": "avatar", "content_type": "application/x-sh"},
            headers=auth_header,
        )
        assert r.status_code == 422

    def test_presigned_url_shape(self, client, auth_header):
        settings = get_settings()
        with (
            patch.object(settings, "s3_bucket", "a2eats-photos"),
            patch.object(uploads, "_client") as mock_client,
        ):
            mock_client.return_value.generate_presigned_url.return_value = (
                "https://a2eats-photos.s3.us-east-2.amazonaws.com/signed?X-Amz-Signature=abc"
            )
            r = client.post(
                "/uploads/presign",
                json={"purpose": "checkin", "content_type": "image/jpeg"},
                headers=auth_header,
            )
        assert r.status_code == 200
        body = r.json()
        assert body["upload_url"].startswith("https://")
        # public URL is deterministic: purpose/user_id/uuid.ext in the bucket
        assert body["public_url"].startswith(
            "https://a2eats-photos.s3.us-east-2.amazonaws.com/checkin/1/"
        )
        assert body["public_url"].endswith(".jpg")

    def test_key_is_unique_per_request(self):
        settings = get_settings()
        with (
            patch.object(settings, "s3_bucket", "bucket"),
            patch.object(uploads, "_client") as mock_client,
        ):
            mock_client.return_value.generate_presigned_url.return_value = "https://signed"
            a = uploads.create_presigned_upload(1, "avatar", "image/png")
            b = uploads.create_presigned_upload(1, "avatar", "image/png")
        assert a["public_url"] != b["public_url"]
