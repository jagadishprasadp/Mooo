"""Database access for Azure SQL (when configured) with a local SQLite fallback.

Repositories write SQL with ``?`` placeholders; :class:`Session` adapts them for pymssql.
"""

import sqlite3
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import pymssql

from config.settings import DATABASE_PATH, get_azure_sql_settings
from repositories.schema import azure_sql_schema, sqlite_schema

# Azure SQL transient codes, including serverless auto-resume (40613).
TRANSIENT_SQL_ERRORS = {4060, 40197, 40501, 40613, 49918, 49919, 49920}
CONNECT_ATTEMPTS = 8
RETRY_DELAY_SECONDS = 15
IDLE_CHECK_SECONDS = 60

IntegrityError = (sqlite3.IntegrityError, pymssql.IntegrityError)
Row = tuple[Any, ...]


class DatabaseUnavailableError(RuntimeError):
    """Azure SQL stayed unavailable after all connection retries."""

# DB-API connections are not thread-safe, so each Streamlit run thread keeps its own.
_thread_state = threading.local()
_schema_lock = threading.Lock()
_initialized_backends: set[str] = set()


class Session:
    """Runs parameterized statements against one open connection."""

    def __init__(self, connection: Any, is_azure: bool) -> None:
        self._connection = connection
        self._is_azure = is_azure

    def _cursor(self, statement: str, params: Sequence[Any]) -> Any:
        cursor = self._connection.cursor()
        sql = statement.replace("?", "%s") if self._is_azure else statement
        cursor.execute(sql, tuple(params))
        return cursor

    def fetch_all(self, statement: str, params: Sequence[Any] = ()) -> list[Row]:
        return [tuple(row) for row in self._cursor(statement, params).fetchall()]

    def fetch_one(self, statement: str, params: Sequence[Any] = ()) -> Row | None:
        row = self._cursor(statement, params).fetchone()
        return tuple(row) if row is not None else None

    def fetch_value(self, statement: str, params: Sequence[Any] = ()) -> Any:
        row = self.fetch_one(statement, params)
        return row[0] if row is not None else None

    def execute(self, statement: str, params: Sequence[Any] = ()) -> None:
        self._cursor(statement, params)

    def insert(self, statement: str, params: Sequence[Any]) -> int:
        cursor = self._cursor(statement, params)
        if self._is_azure:
            cursor.execute("select @@identity")
            return int(cursor.fetchone()[0])
        return int(cursor.lastrowid)


@contextmanager
def transaction() -> Iterator[Session]:
    """Yield a session and commit on success; roll back and reconnect on failure."""
    connection, is_azure = _connection()
    try:
        yield Session(connection, is_azure)
        connection.commit()
    except Exception:
        _rollback(connection)
        raise


def _connection() -> tuple[Any, bool]:
    settings = get_azure_sql_settings()
    if settings is None:
        return _cached_connection("sqlite", _open_sqlite), False
    return _cached_connection("azure", lambda: _open_azure_sql(settings)), True


def _cached_connection(backend: str, open_connection) -> Any:
    connection = getattr(_thread_state, backend, None)
    last_used = getattr(_thread_state, f"{backend}_last_used", 0.0)
    if connection is not None and time.monotonic() - last_used > IDLE_CHECK_SECONDS:
        if not _is_alive(connection):
            _discard_connection(connection)
            connection = None
    if connection is None:
        connection = open_connection()
        setattr(_thread_state, backend, connection)
    setattr(_thread_state, f"{backend}_last_used", time.monotonic())
    _ensure_schema(backend, connection)
    return connection


def _open_sqlite() -> sqlite3.Connection:
    return sqlite3.connect(DATABASE_PATH)


def _open_azure_sql(settings: dict[str, str]) -> pymssql.Connection:
    for attempt in range(1, CONNECT_ATTEMPTS + 1):
        try:
            return pymssql.connect(
                server=settings["server"],
                database=settings["database"],
                user=settings["user"],
                password=settings["password"],
                login_timeout=30,
            )
        except pymssql.OperationalError as error:
            code = error.args[0] if error.args else None
            if code not in TRANSIENT_SQL_ERRORS:
                raise
            if attempt == CONNECT_ATTEMPTS:
                raise DatabaseUnavailableError(f"Azure SQL is still unavailable (error {code}).") from error
            time.sleep(RETRY_DELAY_SECONDS)
    raise DatabaseUnavailableError("Azure SQL connection attempts exhausted.")


def _ensure_schema(backend: str, connection: Any) -> None:
    if backend in _initialized_backends:
        return
    with _schema_lock:
        if backend in _initialized_backends:
            return
        statements = azure_sql_schema() if backend == "azure" else sqlite_schema()
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)
        if backend == "sqlite":
            _add_legacy_sqlite_columns(cursor)
        connection.commit()
        _initialized_backends.add(backend)


def _add_legacy_sqlite_columns(cursor: sqlite3.Cursor) -> None:
    for statement in (
        "alter table memories add column content_hash text",
        "alter table notes add column author_username text",
    ):
        try:
            cursor.execute(statement)
        except sqlite3.OperationalError:
            pass


def _is_alive(connection: Any) -> bool:
    try:
        cursor = connection.cursor()
        cursor.execute("select 1")
        cursor.fetchone()
        return True
    except Exception:
        return False


def _rollback(connection: Any) -> None:
    try:
        connection.rollback()
    except Exception:
        _discard_connection(connection)


def _discard_connection(connection: Any) -> None:
    for backend in ("azure", "sqlite"):
        if getattr(_thread_state, backend, None) is connection:
            setattr(_thread_state, backend, None)
    try:
        connection.close()
    except Exception:
        pass
