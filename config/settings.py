import os

try:
    import streamlit as st
except Exception:  # pragma: no cover - optional in non-Streamlit runtime
    st = None


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
