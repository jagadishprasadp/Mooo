from storage import delete_note, delete_reply, list_media, list_memories, list_notes, list_replies, save_media, save_memory, save_note, save_reply
import base64
from html import escape

import streamlit as st
from storage import delete_memory, delete_note, delete_reply, list_media, list_memories, list_notes, list_replies, save_media, save_memory, save_note, save_reply

PARTNER_NAME = " My Mooo"

st.set_page_config(page_title="For you, always", page_icon="♥", layout="centered", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    :root { --ink:#24201f; --rose:#b84f5c; --line:#eadbd5; --muted:#887b76; }
    .stApp { background:linear-gradient(135deg,#fffaf7 0%,#fff3ee 48%,#f8e6e4 100%); color:var(--ink); }
    .block-container { max-width:760px; padding:2.5rem 1.2rem 4rem; }
    h1,h2,h3 { font-family:Georgia,serif; }
    p,div,label,input,textarea,button { font-family:Arial,sans-serif; }
    h1 { font-size:clamp(3rem,10vw,6.8rem); line-height:.91; margin:.5rem 0 1.2rem; }
    .eyebrow { color:var(--rose); font-size:.68rem; letter-spacing:.16em; text-transform:uppercase; }
    .hero-copy { max-width:520px; color:var(--muted); font-size:1rem; line-height:1.8; }
    .heart,.partner-name { color:var(--rose); }
    .sky { position:relative; height:40px; overflow:hidden; pointer-events:none; }
    .feed-love-birds { display:flex; justify-content:center; gap:1.4rem; height:28px; margin:.35rem 0 -.2rem; color:var(--rose); pointer-events:none; }
    .feed-love-birds span { display:inline-block; font-size:.9rem; animation:feed-bird-float 2s ease-in-out infinite; }
    .feed-love-birds span:nth-child(2) { animation-delay:-.7s; font-size:.7rem; }
    .love-birds { position:absolute; top:12px; left:-54px; width:48px; height:18px; animation:fly-across 16s linear infinite; }
    .bird { position:absolute; top:6px; width:18px; height:8px; opacity:.5; }
    .bird::before,.bird::after { content:""; position:absolute; top:2px; width:9px; height:5px; border-top:2px solid var(--rose); }
    .bird::before { right:8px; transform:rotate(24deg); }
    .bird::after { left:8px; transform:rotate(-24deg); }
    .bird-one { left:0; }.bird-two { left:22px; top:2px; transform:scale(.8); }
    .bird-heart { position:absolute; left:18px; top:-6px; color:var(--rose); }
    .cupid-stage { position:relative; height:34px; }.cupid { position:absolute; right:15%; color:var(--rose); }
    .memories-button button { min-height:4rem; border:0; border-radius:999px; background:#d33145; color:#fff; font-size:1.05rem !important; line-height:1; box-shadow:0 10px 24px rgba(211,49,69,.22); padding:.7rem 1.1rem; }
    .memories-button button:hover { border:0; background:#b9273a; color:#fff; transform:scale(1.05); }
    .memory-grid img { border-radius:16px; }
    .memory-title { color:var(--rose); font-family:Georgia,serif; font-size:2.4rem; text-align:center; margin:1rem 0 2rem; }
    .memory-uploader [data-testid="stFileUploaderDropzoneInstructions"] { display:none; }
    .memory-uploader [data-testid="stFileUploaderDropzone"] { padding:.55rem; background:transparent; border:0; }
    .letter,.feed-item { background:rgba(255,255,255,.74); border:1px solid var(--line); border-radius:20px; padding:1.1rem; box-shadow:0 12px 35px rgba(111,54,47,.06); }
    .letter-line { color:var(--muted); font-size:.8rem; margin-bottom:1rem; }.letter-body,.feed-body { white-space:pre-wrap; font-family:Georgia,serif; line-height:1.55; }
    .note-signature { color:var(--rose); font-family:Georgia,serif; font-size:.95rem; font-style:italic; text-align:right; margin-top:1rem; }
    .note-signature { margin-top:1rem; color:var(--rose); font-family:Georgia,serif; font-size:1.05rem; }
    .note-background { width:100%; max-width:100%; box-sizing:border-box; background-position:center; background-size:contain; background-repeat:no-repeat; min-height:240px; display:flex; flex-direction:column; justify-content:flex-end; overflow:hidden; }
    .feed-item.note-background { min-height:clamp(280px,55vw,520px); background-size:100% 100%; }
    .love-burst { position:relative; height:72px; overflow:hidden; pointer-events:none; }.love-burst span { position:absolute; bottom:-20px; left:50%; color:var(--rose); font-size:1.5rem; animation:float-heart 3.2s ease-out forwards; }
    .love-message { color:var(--rose); font-size:1.65rem; text-align:center; }.love-reaction { animation:love-reaction-out 4s ease-out forwards; overflow:hidden; }
    .feed-heading { margin-top:2.5rem; margin-bottom:1rem; }.divider { border-top:1px solid var(--line); margin:2.4rem 0; }.footer { color:var(--muted); text-align:center; font-size:.72rem; margin-top:2.5rem; }
    .stButton button { border:1px solid var(--line); border-radius:13px; background:#fff; color:var(--ink); min-height:2.7rem; }.primary button { background:var(--rose); color:#fff; }
    @keyframes fly-across { from { left:-54px; } to { left:calc(100% + 54px); } } @keyframes float-heart { from { transform:translateY(0); opacity:0; } to { transform:translateY(-82px); opacity:0; } } @keyframes love-reaction-out { 0%,70% { opacity:1; max-height:120px; } 100% { opacity:0; max-height:0; } }
    @keyframes feed-bird-float { 0%,100% { transform:translateY(2px) rotate(-8deg); } 50% { transform:translateY(-3px) rotate(8deg); } }
    </style>
    """,
    unsafe_allow_html=True,
)

if "show_letter" not in st.session_state:
    st.session_state.show_letter = False
if "saved_note" not in st.session_state:
    st.session_state.saved_note = ""
if "show_composer" not in st.session_state:
    st.session_state.show_composer = False
if "selected_feed_note" not in st.session_state:
    st.session_state.selected_feed_note = None
if "comment_note" not in st.session_state:
    st.session_state.comment_note = None
if "show_replies" not in st.session_state:
    st.session_state.show_replies = None
if "love_blast_note" not in st.session_state:
    st.session_state.love_blast_note = None
if "love_blast_source" not in st.session_state:
    st.session_state.love_blast_source = None
if "show_memories" not in st.session_state:
    st.session_state.show_memories = False
if "memory_upload_version" not in st.session_state:
    st.session_state.memory_upload_version = 0

make_note = False


def note_background(note_id: int) -> str | None:
    for media in list_media(note_id):
        if media["media_type"].startswith("image/") and media["path"].exists():
            encoded = base64.b64encode(media["path"].read_bytes()).decode("ascii")
            return f"data:{media['media_type']};base64,{encoded}"
    return None


def render_note_media(note_id: int, skip_images: bool = False) -> None:
    for media in list_media(note_id):
        if media["media_type"].startswith("video/"):
            st.video(media["path"], width="stretch")
        elif not skip_images:
            st.image(media["path"], caption="A moment I keep close", width="stretch")


def render_love_blast(note_id: int, source: str) -> None:
    if (
        st.session_state.love_blast_note == note_id
        and st.session_state.love_blast_source == source
    ):
        st.markdown(
            '<div class="love-reaction"><div class="love-burst"><span>♥</span><span>♥</span><span>♥</span><span>♥</span><span>♥</span></div><div class="love-message">Love you, Mooo ♥</div></div>',
            unsafe_allow_html=True,
        )
        st.session_state.love_blast_note = None
        st.session_state.love_blast_source = None


def set_all_memory_selection(memory_ids: list[int]) -> None:
    selected = st.session_state.get("select_all_memories", False)
    for memory_id in memory_ids:
        st.session_state[f"select_memory_{memory_id}"] = selected


@st.dialog("Delete note?")
def confirm_note_delete(note_id: int) -> None:
    st.write("Do you really want to delete this note and its media?")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Delete", key=f"confirm_note_{note_id}", type="primary", use_container_width=True):
            delete_note(note_id)
            if st.session_state.get("note_id") == note_id:
                st.session_state.show_letter = False
                st.session_state.saved_note = ""
                st.session_state.pop("note_id", None)
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key=f"cancel_note_{note_id}", use_container_width=True):
            st.rerun()


@st.dialog("Delete reply?")
def confirm_reply_delete(reply_id: int) -> None:
    st.write("Do you really want to delete this reply?")
    confirm_col, cancel_col = st.columns(2)
    with confirm_col:
        if st.button("Delete", key=f"confirm_reply_{reply_id}", type="primary", use_container_width=True):
            delete_reply(reply_id)
            st.rerun()
    with cancel_col:
        if st.button("Cancel", key=f"cancel_reply_{reply_id}", use_container_width=True):
            st.rerun()


st.markdown('<div class="eyebrow"><span class="heart">♥</span> a little place for us</div>', unsafe_allow_html=True)
st.markdown('<h1><span class="heart">♥</span> <span class="partner-name">Mooo</span>,<br>always.</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-copy">Every moment with Mooo becomes a memory I hold close. When she is away, I miss her voice, her laugh, and the little pieces of time that feel brighter when we share them.</p>', unsafe_allow_html=True)

_, memories_col = st.columns([3, 1])
with memories_col:
    st.markdown('<div class="memories-button">', unsafe_allow_html=True)
    if st.button("♥ Open our memory", key="open_memories", help="Open our memories"):
        st.session_state.show_memories = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="sky" aria-hidden="true"><span class="love-birds"><span class="bird bird-one"></span><span class="bird bird-two"></span><span class="bird-heart">♥</span></span></div>', unsafe_allow_html=True)
st.markdown('<div class="cupid-stage" aria-hidden="true"><span class="cupid">♥</span></div>', unsafe_allow_html=True)

if st.session_state.show_memories:
    if st.button("♥ Back to feed", key="back_from_memories_top"):
        st.session_state.show_memories = False
        st.rerun()
    st.markdown('<div class="memory-title">Our memories ♥</div>', unsafe_allow_html=True)
    if st.session_state.get("memory_delete_pending"):
        st.warning("Delete all selected memories permanently?")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("Yes, delete all", type="primary", key="confirm_memory_delete_top"):
                for memory_id in st.session_state.get("selected_memory_ids", []):
                    delete_memory(memory_id)
                st.session_state.memory_delete_pending = False
                st.session_state.selected_memory_ids = []
                st.session_state.select_all_memories = False
                st.rerun()
        with cancel_col:
            if st.button("Cancel", key="cancel_memory_delete_top"):
                st.session_state.memory_delete_pending = False
                st.rerun()
    st.markdown('<div class="memory-uploader">', unsafe_allow_html=True)
    memory_files = st.file_uploader(
        "♥ Add memory",
        type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "webm"],
        accept_multiple_files=True,
        key=f"memory_gallery_upload_{st.session_state.memory_upload_version}",
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    if memory_files:
        added_memory = False
        for memory_file in memory_files:
            added_memory = save_memory(memory_file.name, memory_file.type, memory_file.getvalue()) or added_memory
        if added_memory:
            st.session_state.memory_upload_version += 1
            st.success("Memories added ♥")
            st.rerun()
        else:
            st.info("That memory is already in your collection.")
    memories = list_memories()
    if not memories:
        st.info("Your uploaded memories will appear here.")
    else:
        memory_ids = [media["id"] for media in memories]
        selected_memory_ids = [
            memory_id
            for memory_id in memory_ids
            if st.session_state.get(f"select_memory_{memory_id}", False)
        ]
        toolbar_col, delete_col = st.columns([5, 1])
        with toolbar_col:
            st.checkbox(
                "Select all",
                key="select_all_memories",
                on_change=set_all_memory_selection,
                args=(memory_ids,),
            )
        with delete_col:
            if selected_memory_ids and st.button("🗑", key="delete_selected_memories", help="Delete selected memories"):
                st.session_state.selected_memory_ids = selected_memory_ids
                st.session_state.memory_delete_pending = True
                st.rerun()
        memory_columns = st.columns(2)
        for index, media in enumerate(memories):
            with memory_columns[index % 2]:
                selected = st.checkbox(
                    "Select",
                    key=f"select_memory_{media['id']}",
                    label_visibility="collapsed",
                )
                if media["media_type"].startswith("video/"):
                    st.video(media["path"])
                else:
                    st.image(media["path"], caption="A moment with Mooo", width="stretch")
    st.stop()

add_note_col, _ = st.columns([1, 5])
with add_note_col:
    if st.button("♥", help="Add a note", key="open_note", use_container_width=True):
        st.session_state.show_composer = not st.session_state.show_composer

if st.session_state.show_composer:
    with st.form("love_note"):
        st.markdown(f'<div class="eyebrow"><span class="heart">♥</span> a note for <span class="partner-name">{PARTNER_NAME}</span></div>', unsafe_allow_html=True)
        feeling = st.selectbox(
            "What are you feeling today?",
            [
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
            ],
        )
        note = st.text_area("What did you miss about Mooo?", placeholder="I missed your voice, your laugh, and the way you make an ordinary day feel lighter...", height=170)
        memory = st.file_uploader("Add a memory (optional)", type=["png", "jpg", "jpeg", "webp", "mp4", "mov", "webm"], help="Images and videos are saved with your note.")
        st.markdown('<div class="primary">', unsafe_allow_html=True)
        make_note = st.form_submit_button("Make it beautiful", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

if make_note:
    if not note.strip():
        st.warning(f"Add a few words for {PARTNER_NAME} first.")
    else:
        st.session_state.partner = PARTNER_NAME
        st.session_state.feeling = feeling
        st.session_state.saved_note = note.strip()
        st.session_state.note_id = save_note(PARTNER_NAME, feeling, st.session_state.saved_note)
        if memory:
            save_media(st.session_state.note_id, memory.name, memory.type, memory.getvalue())
        st.session_state.show_composer = False

latest_notes = list_notes()

st.markdown('<div class="eyebrow feed-heading"><span class="heart">♥</span> our little feed</div>', unsafe_allow_html=True)
saved_notes = latest_notes
if not saved_notes:
    st.caption("Your saved notes will appear here.")
else:
    for saved in saved_notes[:10]:
        background = note_background(saved["id"])
        image_media = next(
            (
                media
                for media in list_media(saved["id"])
                if media["media_type"].startswith("image/") and media["path"].exists()
            ),
            None,
        )
        background_style = (
            f' style="background-image:linear-gradient(135deg,rgba(255,250,247,.94),rgba(255,243,238,.76)),url(\'{background}\');"'
            if background
            else ""
        )
        note_is_open = st.session_state.selected_feed_note == saved["id"]
        if image_media and not note_is_open:
            st.image(image_media["path"], width="stretch")
            image_action_col, comment_action_col, replies_action_col, delete_action_col, _ = st.columns([1, 1, 1, 1, 2])
            with image_action_col:
                if st.button("💌", key=f"open_note_{saved['id']}", help="Open my love note"):
                    st.session_state.selected_feed_note = saved["id"]
                    st.rerun()
            with comment_action_col:
                if st.button("💬", key=f"comment_note_{saved['id']}", help="Reply to this note"):
                    st.session_state.comment_note = None if st.session_state.comment_note == saved["id"] else saved["id"]
                    st.rerun()
            with replies_action_col:
                if st.button("🗨", key=f"show_replies_{saved['id']}", help="Show all replies"):
                    st.session_state.show_replies = (
                        None if st.session_state.show_replies == saved["id"] else saved["id"]
                    )
                    st.rerun()
            with delete_action_col:
                if st.button("🗑", key=f"delete_saved_image_{saved['id']}", help="Delete this note"):
                    confirm_note_delete(saved["id"])
        elif image_media:
            st.markdown(
                f'<div class="feed-item note-background"{background_style}><div class="letter-line">{escape(saved["feeling"])}</div><div class="feed-body">{escape(saved["body"])}</div><div class="note-signature">J ♥</div></div>',
                unsafe_allow_html=True,
            )
            image_action_col, comment_action_col, replies_action_col, delete_action_col, _ = st.columns([1, 1, 1, 1, 2])
            with image_action_col:
                if st.button("💌", key=f"close_note_{saved['id']}", help="Close my love note"):
                    st.session_state.selected_feed_note = None
                    st.rerun()
            with comment_action_col:
                if st.button("💬", key=f"comment_open_note_{saved['id']}", help="Reply to this note"):
                    st.session_state.comment_note = None if st.session_state.comment_note == saved["id"] else saved["id"]
                    st.rerun()
            with replies_action_col:
                if st.button("🗨", key=f"show_open_replies_{saved['id']}", help="Show all replies"):
                    st.session_state.show_replies = (
                        None if st.session_state.show_replies == saved["id"] else saved["id"]
                    )
                    st.rerun()
            with delete_action_col:
                if st.button("🗑", key=f"delete_saved_open_{saved['id']}", help="Delete this note"):
                    confirm_note_delete(saved["id"])
        else:
            st.markdown(
                f'<div class="feed-item"><div class="letter-line">{escape(saved["feeling"])}</div><div class="feed-body">{escape(saved["body"])}</div><div class="note-signature">J ♥</div></div>',
                unsafe_allow_html=True,
            )
            image_action_col, comment_action_col, replies_action_col, delete_action_col, _ = st.columns([1, 1, 1, 1, 2])
            with comment_action_col:
                if st.button("💬", key=f"comment_text_{saved['id']}", help="Reply to this note"):
                    st.session_state.comment_note = None if st.session_state.comment_note == saved["id"] else saved["id"]
                    st.rerun()
            with replies_action_col:
                if st.button("🗨", key=f"show_text_replies_{saved['id']}", help="Show all replies"):
                    st.session_state.show_replies = (
                        None if st.session_state.show_replies == saved["id"] else saved["id"]
                    )
                    st.rerun()
            with delete_action_col:
                if st.button("🗑", key=f"delete_saved_text_{saved['id']}", help="Delete this note"):
                    confirm_note_delete(saved["id"])
        render_love_blast(saved["id"], "feed")
        render_note_media(saved["id"], skip_images=True)
        st.markdown('<div class="feed-love-birds" aria-hidden="true"><span>♥</span><span>♥</span></div>', unsafe_allow_html=True)
        reply = ""
        send_reply = False
        if st.session_state.comment_note == saved["id"]:
            with st.form(f"reply_{saved['id']}"):
                reply = st.text_area(
                    "Reply to this note",
                    placeholder="I missed you too...",
                    height=90,
                    key=f"reply_text_{saved['id']}",
                )
                send_reply = st.form_submit_button("♥", help="Send your reply")
        if send_reply:
            if not reply.strip():
                st.warning("Write a few words first.")
            else:
                save_reply(saved["id"], reply.strip())
                st.session_state.love_blast_note = saved["id"]
                st.session_state.love_blast_source = "feed"
                st.rerun()
        if st.session_state.show_replies == saved["id"]:
            for saved_reply in list_replies(saved["id"]):
                reply_col, delete_reply_col = st.columns([6, 1])
                with reply_col:
                    st.markdown(
                        f'<div class="letter"><div class="letter-body">{escape(saved_reply["body"])}</div></div>',
                        unsafe_allow_html=True,
                    )
                with delete_reply_col:
                    if st.button("🗑", key=f"delete_feed_reply_{saved_reply['id']}", help="Delete this reply"):
                        confirm_reply_delete(saved_reply["id"])
st.markdown('<div class="footer">Made with a full heart · private on this device</div>', unsafe_allow_html=True)
