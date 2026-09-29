"""Azure Blob Storage access. Every function is a no-op when Blob Storage is not configured."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings

from config.settings import get_azure_storage_settings

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_container: ContainerClient | None = None
_delete_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="blob-delete")


def _container_client() -> ContainerClient | None:
    global _container
    if _container is not None:
        return _container

    settings = get_azure_storage_settings()
    if settings is None:
        return None

    connection_string, container_name = settings
    with _client_lock:
        if _container is None:
            container = BlobServiceClient.from_connection_string(connection_string).get_container_client(
                container_name
            )
            try:
                container.create_container()
            except ResourceExistsError:
                pass
            _container = container
    return _container


def is_configured() -> bool:
    return get_azure_storage_settings() is not None


def upload_blob(blob_name: str, content: bytes, media_type: str) -> None:
    container = _container_client()
    if container is None:
        return
    container.upload_blob(
        blob_name,
        content,
        overwrite=False,
        content_settings=ContentSettings(content_type=media_type),
    )


def download_blob(blob_name: str) -> bytes | None:
    container = _container_client()
    if container is None:
        return None
    try:
        return container.download_blob(blob_name).readall()
    except ResourceNotFoundError:
        return None


def delete_blobs_in_background(blob_names: list[str]) -> None:
    """Delete blobs without blocking the caller; failures are logged."""
    container = _container_client()
    if container is None:
        return
    _delete_executor.submit(_delete_blobs, container, blob_names)


def _delete_blobs(container: ContainerClient, blob_names: list[str]) -> None:
    for blob_name in blob_names:
        try:
            container.delete_blob(blob_name)
        except ResourceNotFoundError:
            pass
        except Exception:
            logger.exception("Failed to delete blob %s", blob_name)
