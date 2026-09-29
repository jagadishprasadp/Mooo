"""Shared Streamlit helpers: styles, session defaults, and cached media."""

from pathlib import Path

import streamlit as st

STYLESHEET = Path(__file__).with_name("styles.css")
PAGE_SIZE = 5

SESSION_DEFAULTS = {
    "show_composer": False,
    "comment_note": None,
    "show_replies": None,
    "love_blast_note": None,
    "show_memories": False,
    "memory_upload_version": 0,
    "memories_page": 1,
    "feed_page": 1,
}


def apply_styles() -> None:
    st.markdown(f"<style>{STYLESHEET.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def init_session_state() -> None:
    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, value)


@st.cache_data(show_spinner=False)
def _read_media(path: str, modified_ns: int) -> bytes:
    return Path(path).read_bytes()


def cached_media(path: Path) -> bytes:
    """Read a media file, cached until the file changes on disk."""
    return _read_media(str(path), path.stat().st_mtime_ns)


def current_page(total_items: int, state_key: str) -> tuple[int, int]:
    """Clamp the stored page for ``state_key`` and return (page, total_pages)."""
    total_pages = max(1, -(-total_items // PAGE_SIZE))
    page = max(1, min(st.session_state[state_key], total_pages))
    st.session_state[state_key] = page
    return page, total_pages


def page_slice(items: list, page: int) -> list:
    start = (page - 1) * PAGE_SIZE
    return items[start:start + PAGE_SIZE]


def render_pagination(state_key: str, page: int, total_pages: int, scope: str = "app") -> None:
    prev_col, label_col, _, next_col, _ = st.columns([1, 1, 2, 1, 1])
    with prev_col:
        if st.button("← Prev", key=f"{state_key}_prev", disabled=page <= 1):
            st.session_state[state_key] = page - 1
            st.rerun(scope=scope)
    with label_col:
        st.caption(f"Page {page}/{total_pages}")
    with next_col:
        if st.button("Next →", key=f"{state_key}_next", disabled=page >= total_pages):
            st.session_state[state_key] = page + 1
            st.rerun(scope=scope)
