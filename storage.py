import hashlib
from io import BytesIO
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pymssql
from PIL import Image
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from repositories.schema import sqlite_schema, azure_sql_schema

DATABASE_PATH = Path(__file__).with_name("notes.db")
MEDIA_DIRECTORY = Path(__file__).with_name("media")


def _thumbnail_name(file_name: str) -> str:
    return f"thumb-{file_name}"


def _make_thumbnail(content: bytes, media_type: str) -> bytes | None:
    if not media_type.startswith("image/"):
        return None
    try:
        with Image.open(BytesIO(content)) as image:
            image.thumbnail((640, 640))
            output = BytesIO()
            image.convert("RGB").save(output, format="JPEG", quality=78, optimize=True)
            return output.getvalue()
    except Exception:
        return None


def _azure_setting(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value
    try:
        import streamlit as st

        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


def database_backend_name() -> str:
    return "azure_sql" if azure_sql_settings() else "sqlite"


def azure_sql_settings() -> dict[str, str] | None:
    server = _azure_setting("AZURE_SQL_SERVER").strip()
    database = _azure_setting("AZURE_SQL_DATABASE").strip()
    user = _azure_setting("AZURE_SQL_USER").strip()
    password = _azure_setting("AZURE_SQL_PASSWORD").strip()
    if not all([server, database, user, password]):
        return None
    return {"server": server, "database": database, "user": user, "password": password}


def azure_sql_connection() -> pymssql.Connection | None:
    config = azure_sql_settings()
    if not config:
        return None
    return pymssql.connect(
        server=config["server"],
        database=config["database"],
        user=config["user"],
        password=config["password"],
        login_timeout=30,
    )


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


def sqlite_connection() -> sqlite3.Connection:
    database = sqlite3.connect(DATABASE_PATH)
    database.row_factory = sqlite3.Row
    for statement in sqlite_schema():
        database.execute(statement)
    try:
        database.execute("alter table memories add column content_hash text")
    except sqlite3.OperationalError:
        pass
    database.commit()
    return database


def ensure_azure_sql_schema(database) -> None:
    cursor = database.cursor()
    for statement in azure_sql_schema():
        cursor.execute(statement)
    database.commit()


def connection():
    if azure_sql_settings():
        database = azure_sql_connection()
        if database is None:
            raise RuntimeError("Azure SQL is configured but the database connection could not be established.")
        ensure_azure_sql_schema(database)
        return database
    return sqlite_connection()


def _delete_uploaded_file(file_name: str | None) -> None:
    if not file_name:
        return

    file_names = [file_name]
    if not file_name.startswith("thumb-"):
        file_names.append(_thumbnail_name(file_name))
    for stored_name in file_names:
        local_path = MEDIA_DIRECTORY / stored_name
        try:
            local_path.unlink(missing_ok=True)
        except Exception:
            pass

    azure = azure_client()
    if azure is None:
        return

    service, container_name = azure
    for stored_name in file_names:
        try:
            service.get_blob_client(container=container_name, blob=stored_name).delete_blob()
        except ResourceNotFoundError:
            pass


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    iterations = 310000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{iterations}${salt.hex()}${digest.hex()}"


def _password_matches(password: str, stored_hash: str) -> bool:
    try:
        iterations_text, salt_text, digest_text = stored_hash.split("$", 2)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_text),
            int(iterations_text),
        ).hex()
        return secrets.compare_digest(candidate, digest_text)
    except (TypeError, ValueError):
        return False


def create_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    role = "admin" if user_count() == 0 else "user"
    created_at = datetime.now(timezone.utc).isoformat()
    password_hash = _password_hash(password)
    try:
        if azure_sql_settings():
            database = connection()
            cursor = database.cursor()
            cursor.execute(
                "insert into users (username, password_hash, role, created_at) values (%s, %s, %s, %s)",
                (username, password_hash, role, created_at),
            )
            database.commit()
            return True
        with connection() as database:
            database.execute(
                "insert into users (username, password_hash, role, created_at) values (?, ?, ?, ?)",
                (username, password_hash, role, created_at),
            )
            database.commit()
            return True
    except (sqlite3.IntegrityError, pymssql.IntegrityError):
        return False


def user_count() -> int:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("select count(*) from users")
        return int(cursor.fetchone()[0])
    with connection() as database:
        return int(database.execute("select count(*) from users").fetchone()[0])


def ensure_admin_user() -> None:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("select count(*) from users where role = %s", ("admin",))
        if int(cursor.fetchone()[0]) == 0:
            cursor.execute("select top 1 id from users order by id")
            first_user = cursor.fetchone()
            if first_user:
                cursor.execute("update users set role = %s where id = %s", ("admin", first_user[0]))
                database.commit()
        return

    with connection() as database:
        admin_count = database.execute(
            "select count(*) from users where role = ?", ("admin",)
        ).fetchone()[0]
        if int(admin_count) == 0:
            first_user = database.execute(
                "select id from users order by id limit 1"
            ).fetchone()
            if first_user:
                database.execute("update users set role = ? where id = ?", ("admin", first_user[0]))
                database.commit()


def get_user_by_id(user_id: int) -> dict | None:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("select id, username, role from users where id = %s", (user_id,))
        row = cursor.fetchone()
    else:
        with connection() as database:
            row = database.execute(
                "select id, username, role from users where id = ?", (user_id,)
            ).fetchone()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "role": row[2]}


def authenticate_user(username: str, password: str) -> dict | None:
    username = username.strip().lower()
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select id, username, password_hash, role from users where username = %s",
            (username,),
        )
        row = cursor.fetchone()
        if not row or not _password_matches(password, row[2]):
            return None
        return {"id": row[0], "username": row[1], "role": row[3]}

    with connection() as database:
        row = database.execute(
            "select id, username, password_hash, role from users where username = ?",
            (username,),
        ).fetchone()
    if not row or not _password_matches(password, row[2]):
        return None
    return {"id": row[0], "username": row[1], "role": row[3]}


def list_users() -> list[dict]:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("select id, username, role, created_at from users order by id")
        rows = cursor.fetchall()
        return [
            {"id": row[0], "username": row[1], "role": row[2], "created_at": row[3]}
            for row in rows
        ]
    with connection() as database:
        rows = database.execute(
            "select id, username, role, created_at from users order by id"
        ).fetchall()
    return [dict(row) for row in rows]


def delete_user(user_id: int, requester_id: int) -> tuple[bool, str]:
    if user_id == requester_id:
        return False, "You cannot delete your own account."

    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("select id, role from users where id = %s", (user_id,))
        target = cursor.fetchone()
        if not target:
            return False, "That user no longer exists."
        if target[1] == "admin":
            cursor.execute("select count(*) from users where role = %s", ("admin",))
            if int(cursor.fetchone()[0]) <= 1:
                return False, "The final administrator cannot be deleted."
        cursor.execute("delete from users where id = %s", (user_id,))
        database.commit()
        return True, "User deleted."

    with connection() as database:
        target = database.execute(
            "select id, role from users where id = ?", (user_id,)
        ).fetchone()
        if not target:
            return False, "That user no longer exists."
        if target["role"] == "admin":
            admin_count = database.execute(
                "select count(*) from users where role = ?", ("admin",)
            ).fetchone()[0]
            if int(admin_count) <= 1:
                return False, "The final administrator cannot be deleted."
        database.execute("delete from users where id = ?", (user_id,))
        database.commit()
    return True, "User deleted."


def save_note(partner: str, feeling: str, body: str) -> int:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "insert into notes (partner, feeling, body, created_at) values (%s, %s, %s, %s)",
            (partner, feeling, body, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        cursor.execute("select @@identity as id")
        row = cursor.fetchone()
        return int(row[0])

    with connection() as database:
        cursor = database.execute(
            "insert into notes (partner, feeling, body, created_at) values (?, ?, ?, ?)",
            (partner, feeling, body, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        return int(cursor.lastrowid)


def list_notes() -> list[dict]:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select id, partner, feeling, body, created_at from notes order by id desc"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "partner": row[1],
                "feeling": row[2],
                "body": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    with connection() as database:
        rows = database.execute(
            "select id, partner, feeling, body, created_at from notes order by id desc"
        ).fetchall()
    return [dict(row) for row in rows]


def delete_note(note_id: int) -> None:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select file_name from note_media where note_id = %s", (note_id,)
        )
        media_rows = cursor.fetchall()
        cursor.execute("delete from replies where note_id = %s", (note_id,))
        cursor.execute("delete from note_media where note_id = %s", (note_id,))
        cursor.execute("delete from notes where id = %s", (note_id,))
        database.commit()
    else:
        with connection() as database:
            media_rows = database.execute(
                "select file_name from note_media where note_id = ?", (note_id,)
            ).fetchall()
            database.execute("delete from replies where note_id = ?", (note_id,))
            database.execute("delete from note_media where note_id = ?", (note_id,))
            database.execute("delete from notes where id = ?", (note_id,))
            database.commit()
    for media_row in media_rows:
        filename = media_row[0] if isinstance(media_row, tuple) else media_row["file_name"]
        _delete_uploaded_file(filename)


def save_media(note_id: int, original_name: str, media_type: str, content: bytes) -> None:
    MEDIA_DIRECTORY.mkdir(exist_ok=True)
    suffix = Path(original_name).suffix.lower()
    file_name = f"{uuid.uuid4().hex}{suffix}"
    local_path = MEDIA_DIRECTORY / file_name
    local_path.write_bytes(content)
    thumbnail = _make_thumbnail(content, media_type)
    thumbnail_name = _thumbnail_name(file_name)
    thumbnail_path = MEDIA_DIRECTORY / thumbnail_name
    if thumbnail:
        thumbnail_path.write_bytes(thumbnail)
    azure = azure_client()
    if azure:
        service, container_name = azure
        service.get_blob_client(container=container_name, blob=file_name).upload_blob(
            content,
            overwrite=False,
            content_settings=ContentSettings(content_type=media_type),
        )
        if thumbnail:
            service.get_blob_client(container=container_name, blob=thumbnail_name).upload_blob(
                thumbnail,
                overwrite=False,
                content_settings=ContentSettings(content_type="image/jpeg"),
            )
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "insert into note_media (note_id, file_name, media_type) values (%s, %s, %s)",
            (note_id, file_name, media_type),
        )
        database.commit()
        return
    with connection() as database:
        database.execute(
            "insert into note_media (note_id, file_name, media_type) values (?, ?, ?)",
            (note_id, file_name, media_type),
        )
        database.commit()


def list_media(note_id: int, include_original: bool = True) -> list[dict]:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select file_name, media_type from note_media where note_id = %s order by id",
            (note_id,),
        )
        rows = cursor.fetchall()
    else:
        with connection() as database:
            rows = database.execute(
                "select file_name, media_type from note_media where note_id = ? order by id",
                (note_id,),
            ).fetchall()
    media = []
    azure = azure_client()
    for row in rows:
        file_name = row[0] if isinstance(row, tuple) else row["file_name"]
        media_type = row[1] if isinstance(row, tuple) else row["media_type"]
        local_path = MEDIA_DIRECTORY / file_name
        if include_original and not local_path.exists() and azure:
            service, container_name = azure
            try:
                local_path.parent.mkdir(exist_ok=True)
                local_path.write_bytes(
                    service.get_blob_client(container=container_name, blob=file_name)
                    .download_blob()
                    .readall()
                )
            except ResourceNotFoundError:
                continue
        thumbnail_path = MEDIA_DIRECTORY / _thumbnail_name(file_name)
        if media_type.startswith("image/") and not thumbnail_path.exists():
            thumbnail = None
            if azure:
                service, container_name = azure
                try:
                    thumbnail = service.get_blob_client(
                        container=container_name, blob=_thumbnail_name(file_name)
                    ).download_blob().readall()
                except ResourceNotFoundError:
                    pass
                if thumbnail is None and not local_path.exists():
                    try:
                        local_path.parent.mkdir(exist_ok=True)
                        local_path.write_bytes(
                            service.get_blob_client(
                                container=container_name, blob=file_name
                            ).download_blob().readall()
                        )
                    except ResourceNotFoundError:
                        pass
            if thumbnail is None and local_path.exists():
                thumbnail = _make_thumbnail(local_path.read_bytes(), media_type)
            if thumbnail:
                thumbnail_path.write_bytes(thumbnail)
        media.append(
            {
                "path": local_path,
                "thumbnail_path": thumbnail_path if media_type.startswith("image/") else local_path,
                "media_type": media_type,
            }
        )
    return media


def save_memory(original_name: str, media_type: str, content: bytes) -> bool:
    content_hash = hashlib.sha256(content).hexdigest()
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select top 1 id from memories where content_hash = %s", (content_hash,)
        )
        duplicate = cursor.fetchone()
    else:
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
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "insert into memories (file_name, media_type, content_hash, created_at) values (%s, %s, %s, %s)",
            (file_name, media_type, content_hash, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        return True
    with connection() as database:
        database.execute(
            "insert into memories (file_name, media_type, content_hash, created_at) values (?, ?, ?, ?)",
            (file_name, media_type, content_hash, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
    return True


def list_memories() -> list[dict]:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select id, file_name, media_type from memories order by id desc"
        )
        rows = cursor.fetchall()
    else:
        with connection() as database:
            rows = database.execute(
                "select id, file_name, media_type from memories order by id desc"
            ).fetchall()
    media = []
    azure = azure_client()
    for row in rows:
        memory_id = row[0] if isinstance(row, tuple) else row["id"]
        file_name = row[1] if isinstance(row, tuple) else row["file_name"]
        media_type = row[2] if isinstance(row, tuple) else row["media_type"]
        local_path = MEDIA_DIRECTORY / file_name
        if not local_path.exists() and azure:
            service, container_name = azure
            try:
                local_path.parent.mkdir(exist_ok=True)
                local_path.write_bytes(
                    service.get_blob_client(container=container_name, blob=file_name)
                    .download_blob()
                    .readall()
                )
            except ResourceNotFoundError:
                continue
        media.append({"id": memory_id, "path": local_path, "media_type": media_type})
    return media


def delete_memory(memory_id: int) -> None:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("select file_name from memories where id = %s", (memory_id,))
        row = cursor.fetchone()
        cursor.execute("delete from memories where id = %s", (memory_id,))
        database.commit()
    else:
        with connection() as database:
            row = database.execute(
                "select file_name from memories where id = ?", (memory_id,)
            ).fetchone()
            database.execute("delete from memories where id = ?", (memory_id,))
            database.commit()
    if not row:
        return
    file_name = row[0] if isinstance(row, tuple) else row["file_name"]
    _delete_uploaded_file(file_name)


def save_reply(note_id: int, body: str) -> int:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "insert into replies (note_id, body, created_at) values (%s, %s, %s)",
            (note_id, body, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        cursor.execute("select @@identity as id")
        row = cursor.fetchone()
        return int(row[0])

    with connection() as database:
        cursor = database.execute(
            "insert into replies (note_id, body, created_at) values (?, ?, ?)",
            (note_id, body, datetime.now(timezone.utc).isoformat()),
        )
        database.commit()
        return int(cursor.lastrowid)


def list_replies(note_id: int) -> list[dict]:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute(
            "select id, note_id, body, created_at from replies where note_id = %s order by id desc",
            (note_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "note_id": row[1],
                "body": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

    with connection() as database:
        rows = database.execute(
            "select id, note_id, body, created_at from replies where note_id = ? order by id desc",
            (note_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_reply(reply_id: int) -> None:
    if azure_sql_settings():
        database = connection()
        cursor = database.cursor()
        cursor.execute("delete from replies where id = %s", (reply_id,))
        database.commit()
        return

    with connection() as database:
        database.execute("delete from replies where id = ?", (reply_id,))
        database.commit()
