import logging
import uuid
from typing import Protocol

import boto3
import httpx
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger("vcontent.storage")


class Storage(Protocol):
    def ensure_bucket(self) -> None: ...
    def upload(self, key: str, data: bytes, content_type: str) -> str: ...
    def download(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def presign(self, key: str, expires: int = 3600) -> str: ...
    def health(self) -> bool: ...


class S3Storage:
    def __init__(self) -> None:
        self.bucket = settings.s3_bucket
        self.internal = self._client(settings.s3_endpoint)
        self.public = self._client(settings.s3_public_endpoint)

    def _client(self, endpoint: str):
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def ensure_bucket(self) -> None:
        try:
            self.internal.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.internal.create_bucket(Bucket=self.bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        self.internal.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def download(self, key: str) -> bytes:
        obj = self.internal.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self.internal.delete_object(Bucket=self.bucket, Key=key)

    def presign(self, key: str, expires: int = 3600) -> str:
        return self.public.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def health(self) -> bool:
        try:
            self.internal.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            logger.exception("storage health falhou")
            return False


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def ensure_bucket(self) -> None:
        return None

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        self.objects[key] = (data, content_type)
        return key

    def download(self, key: str) -> bytes:
        item = self.objects.get(key)
        if item is None:
            raise FileNotFoundError(key)
        return item[0]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def presign(self, key: str, expires: int = 3600) -> str:
        return f"memory://{key}"

    def health(self) -> bool:
        return True


_storage: Storage | None = None


class BlobStorage:
    def __init__(self) -> None:
        self.token = settings.blob_read_write_token
        self.api = "https://vercel.com/api/blob"

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {"authorization": f"Bearer {self.token}", "x-api-version": "13"}
        if extra:
            headers.update(extra)
        return headers

    def health(self) -> bool:
        try:
            response = httpx.get(self.api, params={"limit": "1"}, headers=self._headers(), timeout=15)
            return response.status_code == 200
        except Exception:
            logger.exception("blob health falhou")
            return False

    def ensure_bucket(self) -> None:
        if not self.health():
            raise RuntimeError("Vercel Blob indisponível")

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        response = httpx.put(
            f"{self.api}/",
            params={"pathname": key},
            content=data,
            headers=self._headers(
                {
                    "x-vercel-blob-access": "public",
                    "x-content-type": content_type,
                    "x-add-random-suffix": "1",
                }
            ),
            timeout=180,
        )
        if response.status_code >= 400:
            raise RuntimeError(response.text[:300])
        url = response.json().get("url")
        if not isinstance(url, str) or not url:
            raise RuntimeError("O armazenamento não devolveu a URL do arquivo.")
        return url

    def download(self, key: str) -> bytes:
        response = httpx.get(key, timeout=60)
        if response.status_code >= 400:
            raise FileNotFoundError(key)
        return response.content

    def delete(self, key: str) -> None:
        if not key.startswith("http"):
            return
        httpx.post(
            f"{self.api}/delete",
            json={"urls": [key]},
            headers=self._headers({"content-type": "application/json"}),
            timeout=30,
        )

    def presign(self, key: str, expires: int = 3600) -> str:
        return key


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = BlobStorage() if settings.blob_read_write_token else S3Storage()
    return _storage


def set_storage(storage: Storage) -> None:
    global _storage
    _storage = storage


def new_key(prefix: str, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"
