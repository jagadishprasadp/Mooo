import sqlite3
from pathlib import Path

import pymssql

from config.settings import get_azure_sql_settings
from repositories.schema import azure_sql_schema, sqlite_schema

DATABASE_PATH = Path(__file__).resolve().parents[1] / "notes.db"


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


def azure_sql_connection() -> pymssql.Connection | None:
    config = get_azure_sql_settings()
    if not config:
        return None

    try:
        return pymssql.connect(
            server=config["server"],
            database=config["database"],
            user=config["user"],
            password=config["password"],
            login_timeout=30,
        )
    except Exception:
        return None


def ensure_azure_sql_schema(database) -> None:
    cursor = database.cursor()
    for statement in azure_sql_schema():
        cursor.execute(statement)
    database.commit()


def connection():
    azure = azure_sql_connection()
    if azure is not None:
        ensure_azure_sql_schema(azure)
        return azure
    return sqlite_connection()
