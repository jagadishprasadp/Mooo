"""Mooo: a private Streamlit space for love notes and shared memories."""

import streamlit as st

from repositories.database import DatabaseUnavailableError
from services import accounts
from ui import auth, feed
from ui.common import apply_styles, init_session_state
from ui.memories import render_memories_page


def main() -> None:
    st.set_page_config(page_title="For you, always", page_icon="♥", layout="centered", initial_sidebar_state="expanded")
    apply_styles()
    try:
        _render_app()
    except DatabaseUnavailableError:
        _render_database_unavailable()


def _render_app() -> None:
    accounts.ensure_admin_exists()
    user = auth.current_user()
    if user is None:
        auth.render_sign_in()
        return

    init_session_state()
    auth.render_sidebar(user)
    auth.render_logout_button()
    auth.render_admin_button(user)

    if st.session_state.show_memories:
        render_memories_page()
        return

    feed.render_header()
    feed.render_composer()
    feed.render_feed()
    feed.render_footer()


def _render_database_unavailable() -> None:
    st.warning(
        "Our database is waking up after a nap. This usually takes a minute or two — please try again shortly.",
        icon="💤",
    )
    if st.button("Try again ♥", type="primary"):
        st.rerun()


if __name__ == "__main__":
    main()
