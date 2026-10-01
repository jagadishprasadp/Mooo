"""Sign-in, registration, sidebar, and the admin panel."""

import hashlib
import secrets

import streamlit as st
from streamlit_cookies_controller import CookieController

from repositories import sessions
from services import accounts
from services import media

AUTH_COOKIE = "mooo_auth"
COOKIE_PROBE_KEY = "auth_cookie_probe_started"


def _cookies() -> CookieController:
    return CookieController()


def _get_cookie(name: str) -> str | None:
    controller = _cookies()
    if not st.session_state.get(COOKIE_PROBE_KEY):
        st.session_state[COOKIE_PROBE_KEY] = True
        st.stop()
    if controller.getAll() is None:
        st.stop()
    value = controller.get(name)
    return str(value) if value else None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def current_user() -> dict | None:
    """Return the signed-in user, refreshed from the database so role changes apply."""
    stored = st.session_state.get("auth_user")
    if not stored:
        token = _get_cookie(AUTH_COOKIE)
        if token:
            user_id = sessions.find_user_id(_token_hash(token))
            if user_id is not None:
                stored = accounts.get_user(user_id)
                if stored:
                    st.session_state.auth_user = stored
    if not stored:
        return None
    user = accounts.get_user(stored["id"])
    if user is None:
        st.session_state.pop("auth_user", None)
        return None
    st.session_state.auth_user = user
    return user


def render_sign_in() -> None:
    st.markdown('<div class="eyebrow"><span class="heart">♥</span> a private place</div>', unsafe_allow_html=True)
    st.markdown('<h1><span class="heart">♥</span> Welcome<br>to Mooo.</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-copy">Sign in to keep your notes and memories close.</p>', unsafe_allow_html=True)
    sign_in_tab, register_tab = st.tabs(["Sign in", "Create account"])
    with sign_in_tab:
        _render_sign_in_form()
    with register_tab:
        _render_registration_form()


def _render_sign_in_form() -> None:
    with st.form("login_form"):
        username = st.text_input("Username", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
    if not submitted:
        return
    user = accounts.authenticate(username, password)
    if user is None:
        st.error("That username or password is not correct.")
        return
    st.session_state.auth_user = user
    token = secrets.token_urlsafe(32)
    sessions.create(user["id"], _token_hash(token))
    _cookies().set(AUTH_COOKIE, token, max_age=sessions.SESSION_DAYS * 24 * 60 * 60)


def _render_registration_form() -> None:
    if not accounts.has_users():
        st.info("The first account becomes the administrator.")
    with st.form("create_account_form"):
        username = st.text_input("Choose a username", autocomplete="username")
        password = st.text_input("Choose a password", type="password", autocomplete="new-password")
        confirm_password = st.text_input("Confirm password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Create account", use_container_width=True)
    if not submitted:
        return
    error = accounts.validate_registration(username, password, confirm_password)
    if error:
        st.error(error)
    elif not accounts.register(username, password):
        st.error("That username is already registered.")
    else:
        st.success("Account created. You can sign in now.")


def render_sidebar(user: dict) -> None:
    with st.sidebar:
        st.caption(f"Signed in as **{user['username']}**")
        if accounts.is_admin(user):
            st.caption("Administrator")
        if st.button("Sign out", use_container_width=True):
            sign_out()


def render_logout_button() -> None:
    st.markdown('<div class="logout-action">', unsafe_allow_html=True)
    signed_out = st.button("Sign out  ♥", key="main_sign_out", help="Sign out of this account")
    st.markdown("</div>", unsafe_allow_html=True)
    if signed_out:
        sign_out()


def sign_out() -> None:
    token = _get_cookie(AUTH_COOKIE)
    if token:
        sessions.delete(_token_hash(token))
        _cookies().remove(AUTH_COOKIE)
    st.session_state.pop("auth_user", None)
    st.rerun()


def render_admin_button(user: dict) -> None:
    if not accounts.is_admin(user):
        return
    admin_col, _ = st.columns([1, 5])
    with admin_col:
        if st.button("Admin panel", key="open_admin_panel", help="Open administrator controls"):
            _admin_panel(user)


@st.dialog("Admin panel", width="large")
def _admin_panel(admin: dict) -> None:
    st.caption(f"Signed in as {admin['username']}")
    st.subheader("Memories background")
    with st.form("memory_background_form"):
        background = st.file_uploader(
            "Upload a background image",
        )
        save_background = st.form_submit_button("Save background", type="primary")
    if save_background:
        if background is None:
            st.warning("Choose an image first.")
        else:
            try:
                media.store_background(background.getvalue())
            except (OSError, ValueError):
                st.error("That image could not be saved. Please choose another image.")
            else:
                st.success("Memories background updated.")
    if st.button("Remove custom background", key="remove_memory_background"):
        media.remove_background()
        st.success("The built-in love background is restored.")

    st.subheader("Reset a user password")
    resettable_users = [user for user in accounts.list_users() if user["id"] != admin["id"]]
    if resettable_users:
        user_by_label = {user["username"]: user for user in resettable_users}
        with st.form("reset_user_password_form"):
            selected_username = st.selectbox("User", list(user_by_label))
            new_password = st.text_input("New password", type="password")
            confirm_password = st.text_input("Confirm new password", type="password")
            reset_password = st.form_submit_button("Reset password", type="primary")
        if reset_password:
            error = accounts.reset_password(
                user_by_label[selected_username]["id"],
                new_password,
                confirm_password,
            )
            if error:
                st.error(error)
            else:
                st.success(f"Password reset for {selected_username}.")
    else:
        st.caption("There are no other users to reset.")

    st.write("Registered users")
    for registered_user in accounts.list_users():
        user_col, role_col, action_col = st.columns([4, 2, 1])
        with user_col:
            st.write(registered_user["username"])
        with role_col:
            st.caption(registered_user["role"])
        with action_col:
            if st.button(
                "Delete",
                key=f"delete_user_{registered_user['id']}",
                disabled=registered_user["id"] == admin["id"],
                help="Delete this user account",
            ):
                deleted, message = accounts.delete_user(registered_user["id"], admin["id"])
                if deleted:
                    st.rerun(scope="fragment")
                st.error(message)
