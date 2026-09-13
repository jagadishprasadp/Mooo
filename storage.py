import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("notes.db")


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
        database.execute("delete from notes where id = ?", (note_id,))
        database.commit()
