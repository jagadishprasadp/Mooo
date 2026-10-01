"""Home feed: header, note composer, feed cards, and note dialogs."""

from collections.abc import Callable
from datetime import datetime
from html import escape

import streamlit as st

from services import notes
from ui.common import cached_media, current_page, page_slice, render_pagination
from ui.memories import open_memories

PARTNER_NAME = " My Mooo"
UPLOAD_TYPES = ["png", "jpg", "jpeg", "webp", "mp4", "mov", "webm"]
FEELINGS = [
    "I miss you",
    "I love you",
    "I am grateful for you",
    "I am proud of you",
    "I cannot wait to see you",
    "I am thinking about you",
    "I feel close to you",
    "I am happy because of you",
    "I feel peaceful with you",
    "I am excited to see you",
    "I am feeling extra romantic",
    "I want to make you smile",
    "I miss your voice",
    "I miss your hugs",
    "I miss your laugh",
    "I am thankful for our memories",
    "I am sorry and thinking of you",
    "I need a little closeness",
    "I want you to know you matter",
]


def render_header() -> None:
    st.markdown('<div class="eyebrow"><span class="heart">♥</span> a little place for us</div>', unsafe_allow_html=True)
    st.markdown('<h1><span class="heart">♥</span> <span class="partner-name">Mooo</span>,<br>always.</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">Every moment with Mooo becomes a memory I hold close. When she is away, '
        "I miss her voice, her laugh, and the little pieces of time that feel brighter when we share them.</p>",
        unsafe_allow_html=True,
    )

    _, memories_col = st.columns([3, 1])
    with memories_col:
        st.markdown('<div class="memories-button">', unsafe_allow_html=True)
        if st.button("♥ Open our memory", key="open_memories"):
            open_memories()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="sky" aria-hidden="true"><span class="love-birds"><span class="bird bird-one"></span>'
        '<span class="bird bird-two"></span><span class="bird-heart">♥</span></span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="cupid-stage" aria-hidden="true"><span class="cupid">♥</span></div>', unsafe_allow_html=True)


def render_composer() -> None:
    toggle_col, _ = st.columns([1, 5])
    with toggle_col:
        if st.button("♥", help="Add a note", key="open_note", use_container_width=True):
            st.session_state.show_composer = not st.session_state.show_composer
    if not st.session_state.show_composer:
        return

    with st.form("love_note"):
        st.markdown(
            f'<div class="eyebrow"><span class="heart">♥</span> a note for '
            f'<span class="partner-name">{escape(PARTNER_NAME)}</span></div>',
            unsafe_allow_html=True,
        )
        feeling = st.selectbox(
            "What are you feeling today?",
            FEELINGS,
            accept_new_options=True,
            placeholder="Choose or type your own feeling...",
        )
        body = st.text_area(
            "What did you miss about Mooo?",
            placeholder="I missed your voice, your laugh, and the way you make an ordinary day feel lighter...",
            height=170,
        )
        attachment = st.file_uploader(
            "Add a memory (optional)", type=UPLOAD_TYPES, help="Images and videos are saved with your note."
        )
        st.markdown('<div class="primary">', unsafe_allow_html=True)
        submitted = st.form_submit_button("Make it beautiful", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if not submitted:
        return
    if not body.strip():
        st.warning(f"Add a few words for {PARTNER_NAME} first.")
        return
    note_id = notes.create_note(PARTNER_NAME, feeling, body.strip())
    if attachment:
        notes.attach_media(note_id, attachment.name, attachment.type, attachment.getvalue())
    st.session_state.show_composer = False


def render_feed() -> None:
    all_notes = notes.list_notes()
    st.markdown('<div class="eyebrow feed-heading"><span class="heart">♥</span> our little feed</div>', unsafe_allow_html=True)
    if not all_notes:
        st.caption("Your saved notes will appear here.")
        return

    page, total_pages = current_page(len(all_notes), "feed_page")
    for note in page_slice(all_notes, page):
        _render_feed_item(note)
    render_pagination("feed_page", page, total_pages)


def render_footer() -> None:
    st.markdown('<div class="footer">Made with a full heart · private on this device</div>', unsafe_allow_html=True)


def _render_feed_item(note: dict) -> None:
    image = notes.first_image(note["id"], include_original=False)
    thumbnail = image["thumbnail_path"] if image else None
    has_thumbnail = thumbnail is not None and thumbnail.exists()
    if has_thumbnail:
        st.image(cached_media(thumbnail), width="stretch")
        if st.button("Open note", key=f"open_note_{note['id']}", use_container_width=True):
            _note_dialog(note["id"])
    else:
        _render_text_card(note)

    _render_love_blast(note["id"])
    for video_path in notes.list_note_videos(note["id"]):
        st.video(video_path, width="stretch")
    st.markdown('<div class="feed-love-birds" aria-hidden="true"><span>♥</span><span>♥</span></div>', unsafe_allow_html=True)

    if has_thumbnail:
        return
    if st.session_state.comment_note == note["id"] and _render_reply_form(note["id"], "feed"):
        st.session_state.love_blast_note = note["id"]
        st.rerun()
    if st.session_state.show_replies == note["id"]:
        _render_reply_thread(note["id"], "feed", _confirm_reply_delete)


def _render_text_card(note: dict) -> None:
    st.markdown(
        f'<div class="feed-item"><div class="letter-line">{escape(note["feeling"])}</div>'
        f'<div class="feed-body">{escape(note["body"])}</div><div class="note-signature">J ♥</div></div>',
        unsafe_allow_html=True,
    )
    _, reply_col, replies_col, delete_col, _ = st.columns([1, 1, 1, 1, 2])
    with reply_col:
        if st.button("💬", key=f"comment_text_{note['id']}", help="Reply to this note"):
            st.session_state.comment_note = _toggle(st.session_state.comment_note, note["id"])
            st.rerun()
    with replies_col:
        if st.button("🗨", key=f"show_text_replies_{note['id']}", help="Show all replies"):
            st.session_state.show_replies = _toggle(st.session_state.show_replies, note["id"])
            st.rerun()
    with delete_col:
        if st.button("🗑", key=f"delete_saved_text_{note['id']}", help="Delete this note"):
            _confirm_note_delete(note["id"])


def _render_reply_form(note_id: int, key: str) -> bool:
    """Render the reply box; return True once a reply has been saved."""
    with st.container(key=f"reply-box-{key}-{note_id}"):
        with st.form(f"{key}_reply_{note_id}", clear_on_submit=True, border=False):
            reply = st.text_area(
                "💌 Write back with love",
                placeholder="I missed you too...",
                height=90,
                key=f"{key}_reply_text_{note_id}",
            )
            submitted = st.form_submit_button("Send with love ♥")
    if not submitted:
        return False
    if not reply.strip():
        st.warning("Write a few words first.")
        return False
    notes.add_reply(note_id, reply.strip())
    return True


def _render_reply_thread(note_id: int, key: str, on_delete: Callable[[int], None]) -> None:
    replies = notes.list_replies(note_id)
    if not replies:
        return
    st.markdown(f'<div class="reply-heading">💕 Little replies · {len(replies)}</div>', unsafe_allow_html=True)
    for reply in replies:
        with st.container(key=f"reply-row-{key}-{reply['id']}"):
            bubble_col, delete_col = st.columns([12, 1], vertical_alignment="center")
            with bubble_col:
                _render_reply(reply)
            with delete_col:
                if st.button("🗑", key=f"{key}_delete_reply_{reply['id']}", help="Delete this reply"):
                    on_delete(reply["id"])


def _render_reply(reply: dict) -> None:
    sent_on = _format_date(reply.get("created_at"))
    st.markdown(
        '<div class="reply-bubble"><span class="reply-avatar">♥</span><div>'
        f'<div class="reply-text">{escape(reply["body"])}</div>'
        f'<div class="reply-time">{escape(sent_on)}</div></div></div>',
        unsafe_allow_html=True,
    )


def _format_date(value) -> str:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return ""
    return value.strftime("%b %d, %Y") if isinstance(value, datetime) else ""


def _render_love_blast(note_id: int) -> None:
    if st.session_state.love_blast_note != note_id:
        return
    st.markdown(
        '<div class="love-reaction"><div class="love-burst">'
        "<span>♥</span><span>♥</span><span>♥</span><span>♥</span><span>♥</span>"
        '</div><div class="love-message">Love you, Mooo ♥</div></div>',
        unsafe_allow_html=True,
    )
    st.session_state.love_blast_note = None


def _toggle(current: int | None, note_id: int) -> int | None:
    return None if current == note_id else note_id


@st.dialog("Mooo note", width="large")
def _note_dialog(note_id: int) -> None:
    note = notes.get_note(note_id)
    if note is None:
        st.info("This note is no longer available.")
        return

    image = notes.first_image(note_id)
    if image and image["path"].exists():
        st.image(cached_media(image["path"]), width="stretch")
    st.caption(note["feeling"])
    st.markdown(f'<div class="letter-body">{escape(note["body"])}</div>', unsafe_allow_html=True)

    if _render_reply_form(note_id, "dialog"):
        st.rerun(scope="fragment")
    # A dialog cannot open another dialog, so replies here are deleted without confirmation.
    _render_reply_thread(note_id, "dialog", _delete_reply_in_dialog)

    st.divider()
    if st.button("Delete note and media", key=f"dialog_delete_note_{note_id}"):
        notes.delete_note(note_id)
        st.rerun()


def _delete_reply_in_dialog(reply_id: int) -> None:
    notes.delete_reply(reply_id)
    st.rerun(scope="fragment")


@st.dialog("Delete note?")
def _confirm_note_delete(note_id: int) -> None:
    st.write("Do you really want to delete this note and its media?")
    _render_confirmation(f"note_{note_id}", lambda: notes.delete_note(note_id))


@st.dialog("Delete reply?")
def _confirm_reply_delete(reply_id: int) -> None:
    st.write("Do you really want to delete this reply?")
    _render_confirmation(f"reply_{reply_id}", lambda: notes.delete_reply(reply_id))


def _render_confirmation(key: str, on_confirm) -> None:
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Delete", key=f"confirm_{key}", type="primary", use_container_width=True):
            on_confirm()
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key=f"cancel_{key}", use_container_width=True):
            st.rerun()
