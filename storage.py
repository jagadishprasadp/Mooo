import sqlite3
import uuid
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

DATABASE_PATH = Path(__file__).with_name("notes.db")
MEDIA_DIRECTORY = Path(__file__).with_name("media")


def _azure_setting(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


def azure_client() -> tuple[BlobServiceClient, str] | None:
    connection_string = _azure_setting("AZURE_STORAGE_CONNECTION_STRING")
    container_name = _azure_setting("AZURE_STORAGE_CONTAINER")
    if not connection_string or not container_name:
        return None
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(container_name)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    return service, container_name


def connection() -> sqlite3.Connection:
    database = sqlite3.connect(DATABASE_PATH)
    database.row_factory = sqlite3.Row
    database.execute(
        """
        create table if not exists notes (
            id integer primary key autoincrement,
            partner text not null,
            feeling text not null,
            body text not null,
            created_at text not null
        )
        """
    )
    database.execute(
        """
        create table if not exists replies (
            id integer primary key autoincrement,
            note_id integer not null,
            body text not null,
            created_at text not null,
            foreign key (note_id) references notes (id)
        )
        """
    )
    database.execute(
        """
        create table if not exists note_media (
            id integer primary key autoincrement,
            note_id integer not null,
            file_name text not null,
            media_type text not null,
            foreign key (note_id) references notes (id)
        )
        """
    )
    database.execute(
        """
        create table if not exists memories (
            id integer primary key autoincrement,
            file_name text not null,
            media_type text not null,
            content_hash text,
            created_at text not null
        )
        """
    )
    try:
        database.execute("alter table memories add column content_hash text")
    except sqlite3.OperationalError:
        pass
    database.commit()
    return database


def save_note(partner: str, feeling: str, body: str) -> int:
    with connection() as database:
        cursor = database.execute(
            "insert into notes (partner, feeling, body, created_at) values (?, ?, ?, ?)",
            (partner, feeling, body, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        return int(cursor.lastrowid)


def list_notes() -> list[dict]:
    with connection() as database:
        rows = database.execute(
            "select id, partner, feeling, body, created_at from notes order by id desc"
        ).fetchall()
    return [dict(row) for row in rows]


def delete_note(note_id: int) -> None:
    with connection() as database:
        media_rows = database.execute(
            "select file_name from note_media where note_id = ?", (note_id,)
        ).fetchall()
        database.execute("delete from replies where note_id = ?", (note_id,))
        database.execute("delete from note_media where note_id = ?", (note_id,))
        database.execute("delete from notes where id = ?", (note_id,))
        database.commit()
    for media_row in media_rows:
        (MEDIA_DIRECTORY / media_row["file_name"]).unlink(missing_ok=True)
        azure = azure_client()
        if azure:
            service, container_name = azure
            try:
                service.get_blob_client(container=container_name, blob=media_row["file_name"]).delete_blob()
            except ResourceNotFoundError:
                pass


def save_media(note_id: int, original_name: str, media_type: str, content: bytes) -> None:
    MEDIA_DIRECTORY.mkdir(exist_ok=True)
    suffix = Path(original_name).suffix.lower()
    file_name = f"{uuid.uuid4().hex}{suffix}"
    local_path = MEDIA_DIRECTORY / file_name
    local_path.write_bytes(content)
    azure = azure_client()
    if azure:
        service, container_name = azure
        service.get_blob_client(container=container_name, blob=file_name).upload_blob(
            content,
            overwrite=False,
            content_settings=ContentSettings(content_type=media_type),
        )
    with connection() as database:
        database.execute(
            "insert into note_media (note_id, file_name, media_type) values (?, ?, ?)",
            (note_id, file_name, media_type),
        )
        database.commit()


def list_media(note_id: int) -> list[dict]:
    with connection() as database:
        rows = database.execute(
            "select file_name, media_type from note_media where note_id = ? order by id",
            (note_id,),
        ).fetchall()
    media = []
    azure = azure_client()
    for row in rows:
        local_path = MEDIA_DIRECTORY / row["file_name"]
        if not local_path.exists() and azure:
            service, container_name = azure
            try:
                local_path.parent.mkdir(exist_ok=True)
                local_path.write_bytes(
                    service.get_blob_client(container=container_name, blob=row["file_name"])
                    .download_blob()
                    .readall()
                )
            except ResourceNotFoundError:
                continue
        media.append({"path": local_path, "media_type": row["media_type"]})
    return media


def save_memory(original_name: str, media_type: str, content: bytes) -> bool:
    content_hash = hashlib.sha256(content).hexdigest()
    with connection() as database:
        duplicate = database.execute(
            "select id from memories where content_hash = ?", (content_hash,)
        ).fetchone()
    if duplicate:
        return False

    MEDIA_DIRECTORY.mkdir(exist_ok=True)
    suffix = Path(original_name).suffix.lower()
    file_name = f"memory-{uuid.uuid4().hex}{suffix}"
    local_path = MEDIA_DIRECTORY / file_name
    local_path.write_bytes(content)
    azure = azure_client()
    if azure:
        service, container_name = azure
        service.get_blob_client(container=container_name, blob=file_name).upload_blob(
            content,
            overwrite=False,
            content_settings=ContentSettings(content_type=media_type),
        )
    with connection() as database:
        database.execute(
            "insert into memories (file_name, media_type, content_hash, created_at) values (?, ?, ?, ?)",
            (file_name, media_type, content_hash, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
    return True


def list_memories() -> list[dict]:
    with connection() as database:
        rows = database.execute(
            "select id, file_name, media_type from memories order by id desc"
        ).fetchall()
    media = []
    azure = azure_client()
    for row in rows:
        local_path = MEDIA_DIRECTORY / row["file_name"]
        if not local_path.exists() and azure:
            service, container_name = azure
            try:
                local_path.parent.mkdir(exist_ok=True)
                local_path.write_bytes(
                    service.get_blob_client(container=container_name, blob=row["file_name"])
                    .download_blob()
                    .readall()
                )
            except ResourceNotFoundError:
                continue
        media.append({"id": row["id"], "path": local_path, "media_type": row["media_type"]})
    return media


def delete_memory(memory_id: int) -> None:
    with connection() as database:
        row = database.execute(
            "select file_name from memories where id = ?", (memory_id,)
        ).fetchone()
        database.execute("delete from memories where id = ?", (memory_id,))
        database.commit()
    if not row:
        return
    (MEDIA_DIRECTORY / row["file_name"]).unlink(missing_ok=True)
    azure = azure_client()
    if azure:
        service, container_name = azure
        try:
            service.get_blob_client(container=container_name, blob=row["file_name"]).delete_blob()
        except ResourceNotFoundError:
            pass


def save_reply(note_id: int, body: str) -> int:
    with connection() as database:
        cursor = database.execute(
            "insert into replies (note_id, body, created_at) values (?, ?, ?)",
            (note_id, body, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        return int(cursor.lastrowid)


def list_replies(note_id: int) -> list[dict]:
    with connection() as database:
        rows = database.execute(
            "select id, note_id, body, created_at from replies where note_id = ? order by id desc",
            (note_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_reply(reply_id: int) -> None:
    with connection() as database:
        database.execute("delete from replies where id = ?", (reply_id,))
        database.commit()
