"""Account registration, sign-in, and administration rules."""

from datetime import datetime, timezone

from repositories import users
from services.security import hash_password, verify_password

MIN_USERNAME_LENGTH = 3
MIN_PASSWORD_LENGTH = 8


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_registration(username: str, password: str, confirm_password: str) -> str | None:
    """Return an error message, or None when the input is valid."""
    if len(normalize_username(username)) < MIN_USERNAME_LENGTH:
        return f"Username must be at least {MIN_USERNAME_LENGTH} characters."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password != confirm_password:
        return "The passwords do not match."
    return None


def register(username: str, password: str) -> bool:
    """Create an account; the first account becomes the administrator."""
    role = users.ADMIN_ROLE if users.count_users() == 0 else users.USER_ROLE
    return users.insert_user(
        normalize_username(username),
        hash_password(password),
        role,
        datetime.now(timezone.utc).isoformat(),
    )


def authenticate(username: str, password: str) -> dict | None:
    found = users.find_credentials(normalize_username(username))
    if found is None:
        return None
    user, password_hash = found
    return user if verify_password(password, password_hash) else None


def has_users() -> bool:
    return users.count_users() > 0


def ensure_admin_exists() -> None:
    users.promote_first_user_if_no_admin()


def get_user(user_id: int) -> dict | None:
    return users.get_user(user_id)


def list_users() -> list[dict]:
    return users.list_users()


def is_admin(user: dict) -> bool:
    return str(user.get("role", "")).strip().lower() == users.ADMIN_ROLE


def delete_user(user_id: int, requester_id: int) -> tuple[bool, str]:
    if user_id == requester_id:
        return False, "You cannot delete your own account."
    return users.delete_user_if_allowed(user_id)
