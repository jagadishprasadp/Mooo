"""Persistence for user accounts."""

from repositories.database import IntegrityError, transaction

ADMIN_ROLE = "admin"
USER_ROLE = "user"


def count_users() -> int:
    with transaction() as session:
        return int(session.fetch_value("select count(*) from users"))


def insert_user(username: str, password_hash: str, role: str, created_at: str) -> bool:
    """Return False when the username is already taken."""
    try:
        with transaction() as session:
            session.execute(
                "insert into users (username, password_hash, role, created_at) values (?, ?, ?, ?)",
                (username, password_hash, role, created_at),
            )
        return True
    except IntegrityError:
        return False


def find_credentials(username: str) -> tuple[dict, str] | None:
    """Return the user and stored password hash for a username."""
    with transaction() as session:
        row = session.fetch_one(
            "select id, username, role, password_hash from users where username = ?",
            (username,),
        )
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "role": row[2]}, row[3]


def get_user(user_id: int) -> dict | None:
    with transaction() as session:
        row = session.fetch_one("select id, username, role from users where id = ?", (user_id,))
    if row is None:
        return None
    return {"id": row[0], "username": row[1], "role": row[2]}


def list_users() -> list[dict]:
    with transaction() as session:
        rows = session.fetch_all("select id, username, role, created_at from users order by id")
    return [
        {"id": row[0], "username": row[1], "role": row[2], "created_at": row[3]}
        for row in rows
    ]


def promote_first_user_if_no_admin() -> None:
    with transaction() as session:
        admin_count = session.fetch_value("select count(*) from users where role = ?", (ADMIN_ROLE,))
        if int(admin_count):
            return
        first_user_id = session.fetch_value("select min(id) from users")
        if first_user_id is not None:
            session.execute("update users set role = ? where id = ?", (ADMIN_ROLE, first_user_id))


def delete_user_if_allowed(user_id: int) -> tuple[bool, str]:
    """Delete a user unless they are the last remaining administrator."""
    with transaction() as session:
        role = session.fetch_value("select role from users where id = ?", (user_id,))
        if role is None:
            return False, "That user no longer exists."
        if role == ADMIN_ROLE:
            admin_count = session.fetch_value("select count(*) from users where role = ?", (ADMIN_ROLE,))
            if int(admin_count) <= 1:
                return False, "The final administrator cannot be deleted."
        session.execute("delete from users where id = ?", (user_id,))
    return True, "User deleted."
