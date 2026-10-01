"""Interactive love-remembrance counter and period metrics."""

import streamlit as st

from services import accounts, love_metrics


def render_love_metrics(user: dict) -> None:
    st.markdown('<div class="eyebrow love-meter-heading">♥ love meter</div>', unsafe_allow_html=True)
    is_admin = accounts.is_admin(user)
    action_col, period_col = st.columns([2, 3], vertical_alignment="bottom")
    remembered = False
    with action_col:
        if is_admin:
            remembered = st.button(
                "I remembered Mooo  ♥",
                key="record_love_reminder",
                type="primary",
                use_container_width=True,
            )
        else:
            st.caption("J's loving thoughts")
    with period_col:
        period = st.segmented_control(
            "Period",
            list(love_metrics.PERIODS),
            default="Day",
            key="love_metric_period",
            label_visibility="collapsed",
        )

    if remembered:
        love_metrics.remember(user["id"])
        st.toast("Another loving thought saved ♥")

    counts = love_metrics.summary()
    selected_period = period or "Day"
    count = counts[selected_period]
    goal = love_metrics.PERIODS[selected_period][1]
    st.markdown(
        f'<div class="love-meter-count"><strong>{count}</strong> loving thoughts this {selected_period.lower()}</div>',
        unsafe_allow_html=True,
    )
    st.progress(min(count / goal, 1.0), text=f"{count} of {goal} love-bar moments")

    columns = st.columns(len(counts))
    for column, (label, value) in zip(columns, counts.items()):
        column.metric(label, value)