"""MinIO storage adapter. delete_file is intentionally not implemented for execution."""

from __future__ import annotations

import io
from typing import Any

from minio import Minio

from app.config import get_settings


class StorageAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def _ensure_bucket(self, bucket: str) -> None:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def list_files(self, bucket: str | None = None, prefix: str = "") -> dict[str, Any]:
        bucket = bucket or self.settings.minio_bucket
        self._ensure_bucket(bucket)
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
        files = [{"name": obj.object_name, "size": obj.size} for obj in objects]
        return {"bucket": bucket, "files": files}

    def read_file(self, object_name: str, bucket: str | None = None) -> dict[str, Any]:
        bucket = bucket or self.settings.minio_bucket
        response = self.client.get_object(bucket, object_name)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
        # Never return full confidential contents in summaries — truncate preview
        preview = data[:500].decode("utf-8", errors="replace")
        return {
            "bucket": bucket,
            "object_name": object_name,
            "size": len(data),
            "preview": preview,
            "content_bytes": data,
        }

    def upload_file(
        self,
        *,
        object_name: str,
        content: str | bytes,
        bucket: str | None = None,
        content_type: str = "text/plain",
    ) -> dict[str, Any]:
        bucket = bucket or self.settings.minio_bucket
        self._ensure_bucket(bucket)
        data = content.encode("utf-8") if isinstance(content, str) else content
        self.client.put_object(
            bucket,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return {"bucket": bucket, "object_name": object_name, "size": len(data), "status": "uploaded"}

    def share_file(
        self,
        *,
        object_name: str,
        recipient: str,
        bucket: str | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        """Synthetic share: create a share receipt object (no public URL)."""
        bucket = bucket or "confidential"
        self._ensure_bucket(bucket)
        receipt = (
            f"SHARE RECEIPT\n"
            f"object={object_name}\n"
            f"recipient={recipient}\n"
            f"note={note}\n"
            f"visibility=restricted\n"
        )
        receipt_name = f"shares/{recipient.replace('@', '_at_')}/{object_name}.share.txt"
        result = self.upload_file(object_name=receipt_name, content=receipt, bucket=bucket)
        return {
            "status": "shared",
            "recipient": recipient,
            "object_name": object_name,
            "receipt": result,
            "public_link": False,
        }
