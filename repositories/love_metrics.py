"""Persistence for timestamped partner-remembrance events."""

from repositories.database import transaction


def insert_reminder(user_id: int, remembered_at: str) -> None:
    with transaction() as session:
        session.execute(
            "insert into love_reminders (user_id, remembered_at) values (?, ?)",
            (user_id, remembered_at),
        )


def count_since(user_id: int, since: str) -> int:
    with transaction() as session:
        return int(
            session.fetch_value(
                "select count(*) from love_reminders where user_id = ? and remembered_at >= ?",
                (user_id, since),
            )
        )