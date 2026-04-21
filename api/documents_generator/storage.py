"""
Unified document storage with S3 + local fallback.

Uses the existing S3Service when S3_BUCKET_NAME is configured.
Falls back to local ``media/`` directory for development environments
where S3 credentials aren't available.

Usage::

    from documents_generator.storage import DocumentStorage

    # Upload
    result = DocumentStorage.upload(file_obj, "policies/abc123/doc.pdf", content_type="application/pdf")
    # → {'key': 'policies/abc123/doc.pdf', 'url': 'https://...'}

    # Download URL
    url = DocumentStorage.get_download_url("policies/abc123/doc.pdf")

    # Delete
    DocumentStorage.delete("policies/abc123/doc.pdf")
"""

import logging
import shutil
from pathlib import Path
from typing import BinaryIO, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(settings.BASE_DIR) / "media"


def _s3_configured() -> bool:
    """Return True if S3 bucket name is set (non-empty)."""
    return bool(getattr(settings, "S3_BUCKET_NAME", None))


class DocumentStorage:
    """
    Thin facade over S3Service with local-filesystem fallback.

    When ``S3_BUCKET_NAME`` env var is set, all operations delegate to
    ``s3.service.S3Service``.  Otherwise files are stored under
    ``<BASE_DIR>/media/<key>`` so development works without AWS credentials.
    """

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    @staticmethod
    def upload(
        file: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Upload *file* under the given *key*.

        Returns ``{'key': ..., 'url': ...}`` on success.
        Raises ``RuntimeError`` on failure.
        """
        if _s3_configured():
            return DocumentStorage._upload_s3(file, key, content_type)
        return DocumentStorage._upload_local(file, key)

    @staticmethod
    def _upload_s3(
        file: BinaryIO, key: str, content_type: Optional[str]
    ) -> dict[str, str]:
        from s3.service import S3Service

        # S3Service generates its own key with UUID — but we want a specific key.
        # Use the low-level client directly for deterministic keys.
        try:
            client = S3Service.get_client()
            bucket = settings.S3_BUCKET_NAME
            extra: dict[str, str] = {}
            if content_type:
                extra["ContentType"] = content_type

            client.upload_fileobj(
                file,
                bucket,
                key,
                ExtraArgs=extra or None,
            )
            url = f"https://{bucket}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
            logger.info("Uploaded to S3: %s", key)
            return {"key": key, "url": url}
        except Exception as exc:
            logger.exception("S3 upload failed for key %s", key)
            raise RuntimeError(f"S3 upload failed: {exc}") from exc

    @staticmethod
    def _upload_local(file: BinaryIO, key: str) -> dict[str, str]:
        dest = MEDIA_ROOT / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file, f)
        logger.info("Saved locally: %s", dest)
        return {"key": key, "url": f"/media/{key}"}

    # ------------------------------------------------------------------
    # Download URL
    # ------------------------------------------------------------------
    @staticmethod
    def get_download_url(key: str, expiration: int = 3600) -> Optional[str]:
        """
        Return a download URL for *key*.

        For S3: a presigned URL valid for *expiration* seconds.
        For local: a ``/media/...`` path (usable behind Django's dev server).
        """
        if _s3_configured():
            from s3.service import S3Service

            url = S3Service.generate_presigned_url(key, expiration=expiration)
            if url is None:
                logger.warning("Failed to generate presigned URL for %s", key)
            return url

        local_path = MEDIA_ROOT / key
        if local_path.exists():
            return f"/media/{key}"
        logger.warning("Local file not found: %s", local_path)
        return None

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------
    @staticmethod
    def delete(key: str) -> bool:
        """
        Delete the object at *key*.

        Returns True on success, False on failure.
        """
        if _s3_configured():
            from s3.service import S3Service

            ok = S3Service.delete_file(key)
            if ok:
                logger.info("Deleted from S3: %s", key)
            else:
                logger.warning("Failed to delete from S3: %s", key)
            return ok

        local_path = MEDIA_ROOT / key
        try:
            local_path.unlink(missing_ok=True)
            logger.info("Deleted locally: %s", local_path)
            return True
        except Exception:
            logger.exception("Failed to delete local file: %s", local_path)
            return False
