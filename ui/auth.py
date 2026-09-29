"""Sign-in, registration, sidebar, and the admin panel."""

import streamlit as st

from services import accounts


def current_user() -> dict | None:
    """Return the signed-in user, refreshed from the database so role changes apply."""
    stored = st.session_state.get("auth_user")
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
    st.rerun()


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
