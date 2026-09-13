import base64
from datetime import date

import streamlit as st
from storage import delete_note, list_notes, save_note

PARTNER_NAME = "Mooo"

st.set_page_config(
    page_title="For you, always",
    page_icon="♥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Playfair+Display:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap');
    :root { --ink:#24201f; --rose:#b84f5c; --soft:#fff6f2; --line:#eadbd5; --muted:#887b76; }
    .stApp { background:linear-gradient(135deg,#fffaf7 0%,#fff3ee 48%,#f8e6e4 100%); color:var(--ink); }
    .block-container { max-width:760px; padding:2.5rem 1.2rem 4rem; }
    .block-container { animation:page-in .7s ease-out both; }
    h1,h2,h3 { font-family:'Playfair Display',serif; letter-spacing:-.03em; }
    p,div,label,input,textarea,button { font-family:'Manrope',sans-serif; }
    h1 { font-size:clamp(3rem,10vw,6.8rem); line-height:.91; margin:.5rem 0 1.2rem; }
    h2 { font-size:2rem; }
    .eyebrow { color:var(--rose); font-family:'DM Mono',monospace; font-size:.68rem; letter-spacing:.16em; text-transform:uppercase; }
    .hero-copy { max-width:520px; color:var(--muted); font-size:1rem; line-height:1.8; animation:copy-in .8s .12s ease-out both; }
    .heart { color:var(--rose); font-size:1.1rem; }
    .partner-name { color:var(--rose); }
    .letter { background:rgba(255,255,255,.74); border:1px solid var(--line); border-radius:24px; padding:1.4rem 1.25rem; box-shadow:0 18px 55px rgba(111,54,47,.08); }
    .letter { animation:letter-in .75s ease-out both; }
    .letter-line { color:var(--muted); font-size:.8rem; margin-bottom:1rem; }
    .letter-body { white-space:pre-wrap; font-family:'Playfair Display',serif; font-size:1.27rem; line-height:1.65; }
    .love-burst { position:relative; height:72px; overflow:hidden; pointer-events:none; margin-bottom:-.4rem; }
    .love-burst span { position:absolute; bottom:-20px; left:50%; color:var(--rose); font-size:1.5rem; animation:float-heart 3.2s ease-out forwards; opacity:0; }
    .love-burst span:nth-child(1) { margin-left:-130px; animation-delay:.05s; font-size:1.15rem; }
    .love-burst span:nth-child(2) { margin-left:-72px; animation-delay:.3s; }
    .love-burst span:nth-child(3) { margin-left:-10px; animation-delay:.12s; font-size:2rem; }
    .love-burst span:nth-child(4) { margin-left:52px; animation-delay:.42s; }
    .love-burst span:nth-child(5) { margin-left:112px; animation-delay:.2s; font-size:1rem; }
    @keyframes float-heart { 0% { transform:translateY(0) rotate(0deg) scale(.5); opacity:0; } 18% { opacity:1; } 100% { transform:translateY(-82px) rotate(22deg) scale(1.15); opacity:0; } }
    @keyframes page-in { from { opacity:0; transform:translateY(14px); } to { opacity:1; transform:translateY(0); } }
    @keyframes copy-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
    @keyframes letter-in { from { opacity:0; transform:translateY(16px) scale(.985); } to { opacity:1; transform:translateY(0) scale(1); } }
    @media (prefers-reduced-motion: reduce) { .love-burst span, .block-container, .hero-copy, .letter { animation:none; opacity:1; transform:none; } }
    .stTextInput input, .stTextArea textarea { border:1px solid var(--line); border-radius:14px; background:rgba(255,255,255,.75); }
    .stButton button { border:1px solid var(--line); border-radius:13px; background:#fff; color:var(--ink); font-weight:700; min-height:2.7rem; }
    .stButton button:hover { border-color:var(--rose); color:var(--rose); }
    .primary button { background:var(--rose); border-color:var(--rose); color:#fff; }
    .primary button:hover { background:#9f404d; border-color:#9f404d; color:#fff; }
    [data-testid="stFileUploader"] section { border:1px dashed var(--line); border-radius:14px; background:rgba(255,255,255,.52); }
    .divider { border-top:1px solid var(--line); margin:2.4rem 0; }
    .footer { color:var(--muted); text-align:center; font-size:.72rem; margin-top:2.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "show_letter" not in st.session_state:
    st.session_state.show_letter = False
if "saved_note" not in st.session_state:
    st.session_state.saved_note = ""

st.markdown('<div class="eyebrow"><span class="heart">♥</span> a little place for us</div>', unsafe_allow_html=True)
st.markdown('<h1><span class="heart">♥</span> <span class="partner-name">Mooo</span>,<br>always.</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-copy">Tell Mooo what you missed over the past two days, in a note that feels like a little piece of you reaching home.</p>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

with st.form("love_note"):
    st.markdown(f'<div class="eyebrow"><span class="heart">♥</span> a note for <span class="partner-name">{PARTNER_NAME}</span></div>', unsafe_allow_html=True)
    feeling = st.selectbox("What are you feeling today?", ["I miss you", "I love you", "I am grateful for you", "I am proud of you", "I cannot wait to see you"])
    note = st.text_area(
        "What did you miss these past two days?",
        placeholder="I missed your voice, your laugh, the way you make an ordinary day feel lighter...",
        height=170,
    )
    memory = st.file_uploader("Add a memory (optional)", type=["png", "jpg", "jpeg", "webp"])
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
        st.session_state.memory = memory
        st.session_state.note_id = save_note(PARTNER_NAME, feeling, st.session_state.saved_note)
        st.session_state.show_letter = True

if st.session_state.show_letter:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="love-burst"><span>♥</span><span>♥</span><span>♥</span><span>♥</span><span>♥</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">your note</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="letter"><div class="letter-line">{date.today().strftime("%B %d, %Y")} · {st.session_state.feeling}</div><div class="letter-body">Dear {st.session_state.partner},<br><br>These past two days, I missed...<br><br>{st.session_state.saved_note}<br><br>Love,<br>always yours ♥</div></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.get("memory"):
        st.image(st.session_state.memory, caption="A moment I keep close", use_container_width=True)
    download_col, delete_col = st.columns(2)
    with download_col:
        st.download_button(
            "Download this note",
            data=f"Dear {st.session_state.partner},\n\nThese past two days, I missed...\n\n{st.session_state.saved_note}\n\nLove, always yours.",
            file_name="a-note-for-you.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with delete_col:
        if st.button("Delete note", use_container_width=True):
            if st.session_state.get("note_id"):
                delete_note(st.session_state.note_id)
            st.session_state.show_letter = False
            st.session_state.saved_note = ""
            st.session_state.pop("partner", None)
            st.session_state.pop("feeling", None)
            st.session_state.pop("memory", None)
            st.session_state.pop("note_id", None)
            st.rerun()

with st.expander("Saved notes on this device"):
    saved_notes = list_notes()
    if not saved_notes:
        st.caption("Your saved notes will appear here.")
    else:
        for saved in saved_notes[:10]:
            st.markdown(f"**{saved['partner']}** · {saved['feeling']}  \n{saved['body']}")

st.markdown('<div class="footer">Made with a full heart · private on this device</div>', unsafe_allow_html=True)
