"""Persistence for notes, their attached media, and replies."""

from repositories.database import transaction


def insert_note(partner: str, feeling: str, body: str, created_at: str) -> int:
    with transaction() as session:
        return session.insert(
            "insert into notes (partner, feeling, body, created_at) values (?, ?, ?, ?)",
            (partner, feeling, body, created_at),
        )


def list_notes() -> list[dict]:
    with transaction() as session:
        rows = session.fetch_all(
            "select id, partner, feeling, body, created_at from notes order by id desc"
        )
    return [
        {"id": row[0], "partner": row[1], "feeling": row[2], "body": row[3], "created_at": row[4]}
        for row in rows
    ]


def get_note(note_id: int) -> dict | None:
    with transaction() as session:
        row = session.fetch_one(
            "select id, partner, feeling, body, created_at from notes where id = ?", (note_id,)
        )
    if row is None:
        return None
    return {"id": row[0], "partner": row[1], "feeling": row[2], "body": row[3], "created_at": row[4]}


def delete_note(note_id: int) -> list[str]:
    """Delete a note with its replies and media rows; return the media file names."""
    with transaction() as session:
        rows = session.fetch_all("select file_name from note_media where note_id = ?", (note_id,))
        session.execute("delete from replies where note_id = ?", (note_id,))
        session.execute("delete from note_media where note_id = ?", (note_id,))
        session.execute("delete from notes where id = ?", (note_id,))
    return [row[0] for row in rows]


def insert_note_media(note_id: int, file_name: str, media_type: str) -> None:
    with transaction() as session:
        session.execute(
            "insert into note_media (note_id, file_name, media_type) values (?, ?, ?)",
            (note_id, file_name, media_type),
        )


def list_note_media(note_id: int) -> list[dict]:
    with transaction() as session:
        rows = session.fetch_all(
            "select file_name, media_type from note_media where note_id = ? order by id",
            (note_id,),
        )
    return [{"file_name": row[0], "media_type": row[1]} for row in rows]


def insert_reply(note_id: int, body: str, created_at: str) -> int:
    with transaction() as session:
        return session.insert(
            "insert into replies (note_id, body, created_at) values (?, ?, ?)",
            (note_id, body, created_at),
        )


def list_replies(note_id: int) -> list[dict]:
    with transaction() as session:
        rows = session.fetch_all(
            "select id, note_id, body, created_at from replies where note_id = ? order by id desc",
            (note_id,),
        )
    return [{"id": row[0], "note_id": row[1], "body": row[2], "created_at": row[3]} for row in rows]


def delete_reply(reply_id: int) -> None:
    with transaction() as session:
        session.execute("delete from replies where id = ?", (reply_id,))
