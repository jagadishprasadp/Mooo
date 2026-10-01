"""Media files: a local disk cache backed by Azure Blob Storage, plus image thumbnails."""

import base64
import subprocess
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image
from pillow_heif import register_heif_opener
from imageio_ffmpeg import get_ffmpeg_exe

from config.settings import MEDIA_DIRECTORY
from services import azure_storage

register_heif_opener()

THUMBNAIL_PREFIX = "thumb-"
THUMBNAIL_SIZE = (640, 640)
THUMBNAIL_QUALITY = 78
BACKGROUND_FILE = "memories-background.jpg"


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
    if is_image(media_type):
        content, original_name, media_type = _normalize_image(original_name, media_type, content)
    file_name = f"{prefix}{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
    _write_local(file_name, content)
    azure_storage.upload_blob(file_name, content, media_type)

    if with_thumbnail and (is_image(media_type) or is_video(media_type)):
        thumbnail = create_thumbnail(content) if is_image(media_type) else create_video_thumbnail(local_path(file_name))
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
        if original is None:
            thumbnail = None
        elif original.suffix.lower() in {".mp4", ".mov", ".webm", ".avi", ".mkv"}:
            thumbnail = create_video_thumbnail(original)
        else:
            thumbnail = create_thumbnail(original.read_bytes())
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


def store_background(content: bytes) -> None:
    with Image.open(BytesIO(content)) as image:
        image.thumbnail((2400, 1600))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=88, optimize=True)
    background = output.getvalue()
    _write_local(BACKGROUND_FILE, background)
    azure_storage.upload_blob(BACKGROUND_FILE, background, "image/jpeg", overwrite=True)


def background_data_uri() -> str | None:
    path = local_path(BACKGROUND_FILE)
    if not path.exists():
        content = azure_storage.download_blob(BACKGROUND_FILE)
        if content is None:
            return None
        _write_local(BACKGROUND_FILE, content)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def remove_background() -> None:
    path = local_path(BACKGROUND_FILE)
    path.unlink(missing_ok=True)
    azure_storage.delete_blobs_in_background([BACKGROUND_FILE])


def create_thumbnail(content: bytes) -> bytes | None:
    try:
        with Image.open(BytesIO(content)) as image:
            image.thumbnail(THUMBNAIL_SIZE)
            output = BytesIO()
            image.convert("RGB").save(output, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            return output.getvalue()
    except Exception:
        return None


def create_video_thumbnail(path: Path) -> bytes | None:
    try:
        result = subprocess.run(
            [
                get_ffmpeg_exe(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                "0.5",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "mjpeg",
                "pipe:1",
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 and result.stdout else None


def _normalize_image(original_name: str, media_type: str, content: bytes) -> tuple[bytes, str, str]:
    """Convert uploaded image formats to browser-friendly JPEG content."""
    with Image.open(BytesIO(content)) as image:
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=90, optimize=True)
    return output.getvalue(), f"{Path(original_name).stem}.jpg", "image/jpeg"


def _write_local(file_name: str, content: bytes) -> None:
    MEDIA_DIRECTORY.mkdir(exist_ok=True)
    local_path(file_name).write_bytes(content)
