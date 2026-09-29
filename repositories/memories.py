"""Persistence for gallery memories."""

from repositories.database import transaction


def memory_exists(content_hash: str) -> bool:
    with transaction() as session:
        return session.fetch_one("select id from memories where content_hash = ?", (content_hash,)) is not None


def insert_memory(file_name: str, media_type: str, content_hash: str, created_at: str) -> None:
    with transaction() as session:
        session.execute(
            "insert into memories (file_name, media_type, content_hash, created_at) values (?, ?, ?, ?)",
            (file_name, media_type, content_hash, created_at),
        )


def list_memories() -> list[dict]:
    with transaction() as session:
        rows = session.fetch_all("select id, file_name, media_type from memories order by id desc")
    return [{"id": row[0], "file_name": row[1], "media_type": row[2]} for row in rows]


def delete_memory(memory_id: int) -> str | None:
    """Delete a memory row and return its file name."""
    with transaction() as session:
        file_name = session.fetch_value("select file_name from memories where id = ?", (memory_id,))
        session.execute("delete from memories where id = ?", (memory_id,))
    return file_name
