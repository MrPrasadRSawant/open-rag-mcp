import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class UploadTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    filename: str
    content_type: str
    size_bytes: int


async def save_upload_file(
    upload: UploadFile,
    *,
    upload_directory: Path,
    max_size_bytes: int,
) -> StoredUpload:
    filename = _safe_filename(upload.filename or "uploaded-document")
    content = await upload.read(max_size_bytes + 1)
    if len(content) > max_size_bytes:
        raise UploadTooLargeError("Uploaded file exceeds the configured size limit")

    upload_directory.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4()}-{filename}"
    path = upload_directory / storage_name
    path.write_bytes(content)

    return StoredUpload(
        path=path,
        filename=filename,
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=len(content),
    )


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return safe or "uploaded-document"
