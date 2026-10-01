"""Memory gallery page."""

import base64

import streamlit as st

from services import media, memories
from ui.common import cached_media, current_page, page_slice, render_pagination

CACHE_KEY = "memories_cache"
CLEAR_SELECTION_KEY = "clear_memory_selection"


def open_memories() -> None:
    st.session_state.show_memories = True
    st.session_state.pop(CACHE_KEY, None)


def render_memories_page() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #fff1f3;
            background-image:
                linear-gradient(rgba(255, 247, 246, .78), rgba(255, 232, 235, .84)),
                url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 800'%3E%3Cdefs%3E%3CradialGradient id='g' cx='50%25' cy='35%25'%3E%3Cstop offset='0' stop-color='%23fffdfb'/%3E%3Cstop offset='1' stop-color='%23f7cbd2'/%3E%3C/radialGradient%3E%3C/defs%3E%3Crect width='1200' height='800' fill='url(%23g)'/%3E%3Cg fill='%23d96b7b' opacity='.28'%3E%3Cpath d='M160 170c-32-48-104 2 0 80 104-78 32-128 0-80z'/%3E%3Cpath d='M970 180c-32-48-104 2 0 80 104-78 32-128 0-80z'/%3E%3Cpath d='M600 530c-32-48-104 2 0 80 104-78 32-128 0-80z'/%3E%3C/g%3E%3Cg fill='none' stroke='%23d96b7b' stroke-width='3' opacity='.2'%3E%3Ccircle cx='600' cy='360' r='190'/%3E%3Ccircle cx='600' cy='360' r='250'/%3E%3C/g%3E%3C/svg%3E");
            background-position: center;
            background-size: cover;
            background-attachment: fixed;
        }
        [data-testid="stAppViewContainer"] > .main { background: transparent; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    background_uri = media.background_data_uri()
    if background_uri:
        st.markdown(
            f"""
            <style>
            [data-testid="stAppViewContainer"] {{
                background-image: linear-gradient(rgba(255, 247, 246, .72), rgba(255, 232, 235, .78)), url("{background_uri}");
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    if st.button("♥ Back to feed", key="back_from_memories_top"):
        st.session_state.show_memories = False
        st.rerun()
    st.markdown('<div class="memory-title">Our memories ♥</div>', unsafe_allow_html=True)
    _clear_deleted_selection()
    _render_uploader()
    _render_gallery()


def _clear_deleted_selection() -> None:
    # Checkbox state can only be reset before the checkboxes render in this run.
    cleared_ids = st.session_state.pop(CLEAR_SELECTION_KEY, None)
    if not cleared_ids:
        return
    st.session_state.pop("select_all_memories", None)
    for memory_id in cleared_ids:
        st.session_state.pop(f"select_memory_{memory_id}", None)


def _render_uploader() -> None:
    st.markdown('<div class="memory-uploader">', unsafe_allow_html=True)
    uploads = st.file_uploader(
        "♥ Add memory",
        accept_multiple_files=True,
        key=f"memory_gallery_upload_{st.session_state.memory_upload_version}",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    if not uploads:
        return
    added = [memories.add_memory(upload.name, upload.type, upload.getvalue()) for upload in uploads]
    if any(added):
        st.session_state.memory_upload_version += 1
        st.session_state.pop(CACHE_KEY, None)
        st.success("Memories added ♥")
        st.rerun()
    st.info("That memory is already in your collection.")


def _cached_memories() -> list[dict]:
    if CACHE_KEY not in st.session_state:
        st.session_state[CACHE_KEY] = memories.list_memories()
    return st.session_state[CACHE_KEY]


def _select_all(memory_ids: list[int]) -> None:
    selected = st.session_state.get("select_all_memories", False)
    for memory_id in memory_ids:
        st.session_state[f"select_memory_{memory_id}"] = selected


@st.fragment
def _render_gallery() -> None:
    items = _cached_memories()
    if not items:
        st.info("Your uploaded memories will appear here.")
        return

    page, total_pages = current_page(len(items), "memories_page")
    page_items = page_slice(items, page)
    page_ids = [item["id"] for item in page_items]
    selected_ids = [memory_id for memory_id in page_ids if st.session_state.get(f"select_memory_{memory_id}")]

    toolbar_col, delete_col = st.columns([5, 1])
    with toolbar_col:
        st.checkbox("Select all", key="select_all_memories", on_change=_select_all, args=(page_ids,))
    with delete_col:
        if selected_ids and st.button("🗑", key="delete_selected_memories", help="Delete selected memories"):
            _confirm_delete(selected_ids)

    columns = st.columns(2)
    for index, item in enumerate(page_items):
        with columns[index % 2]:
            st.checkbox("Select", key=f"select_memory_{item['id']}", label_visibility="collapsed")
            if media.is_video(item["media_type"]):
                st.markdown('<div class="memory-media-frame memory-video-frame">', unsafe_allow_html=True)
                st.video(item["path"])
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                _render_memory_image(item["path"])

    render_pagination("memories_page", page, total_pages, scope="fragment")


def _render_memory_image(path) -> None:
    content = base64.b64encode(cached_media(path)).decode("ascii")
    media_type = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else f"image/{path.suffix.lstrip('.')}"
    st.markdown(
        f'<div class="memory-media-frame"><img src="data:{media_type};base64,{content}" '
        "alt=\"A moment with Mooo\" style=\"object-fit:contain;\"></div>",
        unsafe_allow_html=True,
    )
    st.caption("A moment with Mooo")


@st.dialog("Delete memories?")
def _confirm_delete(memory_ids: list[int]) -> None:
    count = len(memory_ids)
    st.write(f"Delete {count} selected {'memory' if count == 1 else 'memories'} permanently?")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Delete", key="confirm_memory_delete", type="primary", use_container_width=True):
            for memory_id in memory_ids:
                memories.delete_memory(memory_id)
            st.session_state[CLEAR_SELECTION_KEY] = memory_ids
            st.session_state.pop(CACHE_KEY, None)
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key="cancel_memory_delete", use_container_width=True):
            st.rerun()
