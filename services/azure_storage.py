from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from config.settings import get_azure_storage_settings


def azure_client():
    settings = get_azure_storage_settings()
    if settings is None:
        return None

    connection_string, container_name = settings
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(container_name)

    try:
        container.create_container()
    except ResourceExistsError:
        pass

    return service, container_name


def upload_blob(blob_name: str, content: bytes, media_type: str) -> None:
    client = azure_client()
    if client is None:
        return

    service, container_name = client
    service.get_blob_client(container=container_name, blob=blob_name).upload_blob(
        content,
        overwrite=False,
        content_settings=ContentSettings(content_type=media_type),
    )


def download_blob(blob_name: str) -> bytes | None:
    client = azure_client()
    if client is None:
        return None

    service, container_name = client
    try:
        return service.get_blob_client(container=container_name, blob=blob_name).download_blob().readall()
    except ResourceNotFoundError:
        return None


def delete_blob(blob_name: str) -> None:
    client = azure_client()
    if client is None:
        return

    service, container_name = client
    try:
        service.get_blob_client(container=container_name, blob=blob_name).delete_blob()
    except ResourceNotFoundError:
        pass
