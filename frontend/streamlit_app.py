"""Streamlit frontend. Run from the project root:

    streamlit run frontend/streamlit_app.py

The FastAPI backend must be running (uvicorn app.main:app --reload).
"""

import sys
from pathlib import Path

# Make the project root importable (Streamlit only adds this file's folder to sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from frontend import ui  # noqa: E402
from frontend.pages import ALL_PAGES  # noqa: E402

st.set_page_config(page_title="CallFlow AI", page_icon=":material/support_agent:", layout="wide")
ui.inject_css()

with st.sidebar:
    st.html('<div class="cf-brand">CallFlow <span>AI</span></div>'
            '<div class="cf-tagline">Sales QA &amp; lead follow-up copilot</div>')

page = st.navigation(ALL_PAGES)
ui.sidebar_status()
page.run()
