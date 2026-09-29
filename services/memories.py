"""Memory gallery uploads with duplicate detection."""

import hashlib
from datetime import datetime, timezone

from repositories import memories
from services import media

FILE_PREFIX = "memory-"


def add_memory(original_name: str, media_type: str, content: bytes) -> bool:
    """Store a memory; return False when identical content already exists."""
    content_hash = hashlib.sha256(content).hexdigest()
    if memories.memory_exists(content_hash):
        return False
    file_name = media.store(original_name, media_type, content, prefix=FILE_PREFIX)
    memories.insert_memory(file_name, media_type, content_hash, datetime.now(timezone.utc).isoformat())
    return True


def list_memories() -> list[dict]:
    items = []
    for row in memories.list_memories():
        path = media.ensure_local(row["file_name"])
        if path is not None:
            items.append({"id": row["id"], "path": path, "media_type": row["media_type"]})
    return items


def delete_memory(memory_id: int) -> None:
    file_name = memories.delete_memory(memory_id)
    if file_name:
        media.delete(file_name)
