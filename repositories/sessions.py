"""Persistent login sessions stored as hashes rather than raw browser tokens."""

from datetime import datetime, timedelta, timezone

from repositories.database import transaction

SESSION_DAYS = 30


def create(user_id: int, token_hash: str) -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    with transaction() as session:
        session.execute(
            "insert into auth_sessions (token_hash, user_id, expires_at) values (?, ?, ?)",
            (token_hash, user_id, expires_at),
        )


def find_user_id(token_hash: str) -> int | None:
    with transaction() as session:
        row = session.fetch_one(
            "select user_id, expires_at from auth_sessions where token_hash = ?",
            (token_hash,),
        )
    if row is None:
        return None
    try:
        expires_at = datetime.fromisoformat(str(row[1]))
    except ValueError:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        delete(token_hash)
        return None
    return int(row[0])


def delete(token_hash: str) -> None:
    with transaction() as session:
        session.execute("delete from auth_sessions where token_hash = ?", (token_hash,))