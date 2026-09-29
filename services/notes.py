"""Notes, their attached media, and replies."""

from datetime import datetime, timezone
from pathlib import Path

from repositories import notes
from services import media


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_note(partner: str, feeling: str, body: str) -> int:
    return notes.insert_note(partner, feeling, body, _now())


def attach_media(note_id: int, original_name: str, media_type: str, content: bytes) -> None:
    file_name = media.store(original_name, media_type, content, with_thumbnail=True)
    notes.insert_note_media(note_id, file_name, media_type)


def list_notes() -> list[dict]:
    return notes.list_notes()


def get_note(note_id: int) -> dict | None:
    return notes.get_note(note_id)


def delete_note(note_id: int) -> None:
    for file_name in notes.delete_note(note_id):
        media.delete(file_name)


def first_image(note_id: int, include_original: bool = True) -> dict | None:
    """Return the note's first image with local ``path`` and ``thumbnail_path``.

    With ``include_original=False`` only the thumbnail is fetched, which keeps the feed fast.
    """
    for row in notes.list_note_media(note_id):
        if not media.is_image(row["media_type"]):
            continue
        file_name = row["file_name"]
        path = media.ensure_local(file_name) if include_original else media.local_path(file_name)
        if path is None:
            continue
        thumbnail_path = media.ensure_thumbnail(file_name)
        return {"path": path, "thumbnail_path": thumbnail_path or path}
    return None


def list_note_videos(note_id: int) -> list[Path]:
    """Return local paths of a note's videos, downloading only the videos."""
    paths = []
    for row in notes.list_note_media(note_id):
        if media.is_video(row["media_type"]):
            path = media.ensure_local(row["file_name"])
            if path is not None:
                paths.append(path)
    return paths


def add_reply(note_id: int, body: str) -> int:
    return notes.insert_reply(note_id, body, _now())


def list_replies(note_id: int) -> list[dict]:
    return notes.list_replies(note_id)


def delete_reply(reply_id: int) -> None:
    notes.delete_reply(reply_id)
