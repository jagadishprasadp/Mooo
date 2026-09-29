"""Application settings read from environment variables or Streamlit secrets."""

import os
from pathlib import Path

try:
    import streamlit as st
except ImportError:  # pragma: no cover - Streamlit is optional outside the app runtime
    st = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "notes.db"
MEDIA_DIRECTORY = PROJECT_ROOT / "media"


def get_setting(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value

    if st is not None:
        try:
            return str(st.secrets.get(name, ""))
        except Exception:
            return ""

    return ""


def get_azure_sql_settings() -> dict[str, str] | None:
    server = get_setting("AZURE_SQL_SERVER").strip()
    database = get_setting("AZURE_SQL_DATABASE").strip()
    user = get_setting("AZURE_SQL_USER").strip()
    password = get_setting("AZURE_SQL_PASSWORD").strip()

    if not all([server, database, user, password]):
        return None

    return {
        "server": server,
        "database": database,
        "user": user,
        "password": password,
    }


def get_azure_storage_settings() -> tuple[str, str] | None:
    connection_string = get_setting("AZURE_STORAGE_CONNECTION_STRING").strip()
    container_name = get_setting("AZURE_STORAGE_CONTAINER").strip()

    if not connection_string or not container_name:
        return None

    return connection_string, container_name
