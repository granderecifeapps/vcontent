import json
import logging
import time
import uuid
from collections.abc import Iterator
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


class DriveStorage:
    def __init__(self) -> None:
        self._access = ""
        self._exp = 0.0

    def _bearer(self) -> str:
        if self._access and self._exp > time.time() + 60:
            return self._access
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": settings.google_refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        if response.status_code >= 400:
            raise RuntimeError("Não foi possível autorizar o Google Drive.")
        data = response.json()
        self._access = str(data["access_token"])
        self._exp = time.time() + int(data.get("expires_in", 3600))
        return self._access

    def _file_id(self, key: str) -> str:
        if not key.startswith("drive:"):
            raise FileNotFoundError(key)
        return key.split(":", 1)[1]

    def health(self) -> bool:
        try:
            self._bearer()
            return True
        except Exception:
            logger.exception("drive health falhou")
            return False

    def ensure_bucket(self) -> None:
        if not self.health():
            raise RuntimeError("Google Drive indisponível")

    def upload(self, key: str, data: bytes, content_type: str) -> str:
        boundary = "vcontent"
        meta: dict[str, object] = {"name": key.replace("/", "-")}
        if settings.drive_folder_id:
            meta["parents"] = [settings.drive_folder_id]
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
            + json.dumps(meta).encode()
            + f"\r\n--{boundary}\r\nContent-Type: {content_type}\r\n\r\n".encode()
            + data
            + f"\r\n--{boundary}--".encode()
        )
        response = httpx.post(
            "https://www.googleapis.com/upload/drive/v3/files",
            params={"uploadType": "multipart", "fields": "id"},
            content=body,
            headers={"Authorization": f"Bearer {self._bearer()}", "Content-Type": f"multipart/related; boundary={boundary}"},
            timeout=300,
        )
        if response.status_code >= 400:
            raise RuntimeError(response.text[:300])
        file_id = response.json().get("id")
        if not isinstance(file_id, str) or not file_id:
            raise RuntimeError("O Drive não devolveu o arquivo.")
        return f"drive:{file_id}"

    def download(self, key: str) -> bytes:
        file_id = self._file_id(key)
        response = httpx.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"alt": "media"},
            headers={"Authorization": f"Bearer {self._bearer()}"},
            timeout=120,
        )
        if response.status_code >= 400:
            raise FileNotFoundError(key)
        return response.content

    def delete(self, key: str) -> None:
        if not key.startswith("drive:"):
            return
        httpx.delete(
            f"https://www.googleapis.com/drive/v3/files/{self._file_id(key)}",
            headers={"Authorization": f"Bearer {self._bearer()}"},
            timeout=30,
        )

    def presign(self, key: str, expires: int = 21600) -> str:
        from app.security import create_file_token

        token = create_file_token(self._file_id(key), hours=max(1, expires // 3600))
        base = settings.public_api_url.rstrip("/")
        return f"{base}/api/files/{token}" if base else f"/backend/api/files/{token}"

    def open_stream(self, file_id: str, range_header: str | None) -> tuple[int, str, dict[str, str], Iterator[bytes]]:
        token = self._bearer()
        meta = httpx.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            params={"fields": "mimeType,size,name"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if meta.status_code >= 400:
            raise FileNotFoundError(file_id)
        info = meta.json()
        headers = {"Authorization": f"Bearer {token}"}
        if range_header:
            headers["Range"] = range_header
        client = httpx.Client(timeout=None)
        response = client.send(
            client.build_request("GET", f"https://www.googleapis.com/drive/v3/files/{file_id}", params={"alt": "media"}, headers=headers),
            stream=True,
        )
        if response.status_code >= 400:
            response.close()
            client.close()
            raise FileNotFoundError(file_id)

        def chunks() -> Iterator[bytes]:
            try:
                for chunk in response.iter_bytes():
                    yield chunk
            finally:
                response.close()
                client.close()

        out = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300"}
        if response.headers.get("content-range"):
            out["Content-Range"] = response.headers["content-range"]
        length = response.headers.get("content-length") or (str(info["size"]) if info.get("size") and not range_header else "")
        if length:
            out["Content-Length"] = length
        return response.status_code, str(info.get("mimeType") or "application/octet-stream"), out, chunks()


def drive_enabled() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret and settings.google_refresh_token)


def storage_backend_name() -> str:
    if drive_enabled():
        return "google_drive"
    if settings.blob_read_write_token:
        return "vercel_blob"
    return "s3"


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        if drive_enabled():
            _storage = DriveStorage()
        elif settings.blob_read_write_token:
            _storage = BlobStorage()
        else:
            _storage = S3Storage()
    return _storage


def set_storage(storage: Storage) -> None:
    global _storage
    _storage = storage


def new_key(prefix: str, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    return f"{prefix}/{uuid.uuid4().hex}.{ext}"
