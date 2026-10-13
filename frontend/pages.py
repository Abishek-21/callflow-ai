"""App pages, defined once so views can link to each other with st.switch_page."""

import streamlit as st

from frontend.views import coaching, dashboard, evaluate, history

EVALUATE = st.Page(
    evaluate.render, title="Evaluate call", icon=":material/rate_review:", url_path="evaluate", default=True
)
DASHBOARD = st.Page(dashboard.render, title="Dashboard", icon=":material/space_dashboard:", url_path="dashboard")
HISTORY = st.Page(history.render, title="Call history", icon=":material/history:", url_path="history")
COACHING = st.Page(coaching.render, title="Coaching", icon=":material/school:", url_path="coaching")

ALL_PAGES = [EVALUATE, DASHBOARD, HISTORY, COACHING]
