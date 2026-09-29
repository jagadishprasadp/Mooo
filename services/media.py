"""Media files: a local disk cache backed by Azure Blob Storage, plus image thumbnails."""

import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image

from config.settings import MEDIA_DIRECTORY
from services import azure_storage

THUMBNAIL_PREFIX = "thumb-"
THUMBNAIL_SIZE = (640, 640)
THUMBNAIL_QUALITY = 78


def is_image(media_type: str) -> bool:
    return media_type.startswith("image/")


def is_video(media_type: str) -> bool:
    return media_type.startswith("video/")


def local_path(file_name: str) -> Path:
    return MEDIA_DIRECTORY / file_name


def thumbnail_name(file_name: str) -> str:
    return f"{THUMBNAIL_PREFIX}{file_name}"


def store(original_name: str, media_type: str, content: bytes, prefix: str = "", with_thumbnail: bool = False) -> str:
    """Save media locally and to Blob Storage; return the generated file name."""
    file_name = f"{prefix}{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
    _write_local(file_name, content)
    azure_storage.upload_blob(file_name, content, media_type)

    if with_thumbnail and is_image(media_type):
        thumbnail = create_thumbnail(content)
        if thumbnail:
            _write_local(thumbnail_name(file_name), thumbnail)
            azure_storage.upload_blob(thumbnail_name(file_name), thumbnail, "image/jpeg")
    return file_name


def ensure_local(file_name: str) -> Path | None:
    """Return the cached file path, downloading it from Blob Storage if needed."""
    path = local_path(file_name)
    if path.exists():
        return path
    content = azure_storage.download_blob(file_name)
    if content is None:
        return None
    _write_local(file_name, content)
    return path


def ensure_thumbnail(file_name: str) -> Path | None:
    """Return a cached thumbnail, downloading or generating it when missing."""
    path = local_path(thumbnail_name(file_name))
    if path.exists():
        return path

    thumbnail = azure_storage.download_blob(thumbnail_name(file_name))
    if thumbnail is None:
        original = ensure_local(file_name)
        thumbnail = create_thumbnail(original.read_bytes()) if original else None
    if thumbnail is None:
        return None
    _write_local(thumbnail_name(file_name), thumbnail)
    return path


def delete(file_name: str) -> None:
    """Remove a file and its thumbnail from the local cache and Blob Storage."""
    names = [file_name, thumbnail_name(file_name)]
    for name in names:
        local_path(name).unlink(missing_ok=True)
    azure_storage.delete_blobs_in_background(names)


def create_thumbnail(content: bytes) -> bytes | None:
    try:
        with Image.open(BytesIO(content)) as image:
            image.thumbnail(THUMBNAIL_SIZE)
            output = BytesIO()
            image.convert("RGB").save(output, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            return output.getvalue()
    except Exception:
        return None


def _write_local(file_name: str, content: bytes) -> None:
    MEDIA_DIRECTORY.mkdir(exist_ok=True)
    local_path(file_name).write_bytes(content)
