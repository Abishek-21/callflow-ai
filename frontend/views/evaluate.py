"""Evaluate page: paste/upload a transcript (or load a demo), evaluate, review results."""

import streamlit as st

from app.sample_data import DEMO_CALLS
from app.schemas import BusinessType
from frontend import api_client, ui
from frontend.result_view import render_result

MIN_TRANSCRIPT_CHARS = 50
DEMO_BUTTONS = {
    "roofing_strong": "Roofing · strong call",
    "hvac_weak": "HVAC · weak call",
    "plumbing_objection": "Plumbing · price objection",
}


def _init_state() -> None:
    st.session_state.setdefault("eval_transcript", "")
    st.session_state.setdefault("eval_business_type", BusinessType.ROOFING.value)
    st.session_state.setdefault("eval_agent", "")
    st.session_state.setdefault("eval_date", None)
    st.session_state.setdefault("eval_result", None)
    st.session_state.setdefault("eval_error", None)


def _load_demo(key: str) -> None:
    call = next(c for c in DEMO_CALLS if c["key"] == key)
    st.session_state.eval_transcript = call["transcript"].strip()
    st.session_state.eval_business_type = call["business_type"].value
    st.session_state.eval_agent = call["agent_name"]
    st.session_state.eval_date = call["call_date"]


def _load_upload() -> None:
    upload = st.session_state.get("eval_upload")
    if upload is not None:
        st.session_state.eval_transcript = upload.getvalue().decode("utf-8", errors="replace").strip()


def _clear() -> None:
    for k in ("eval_transcript", "eval_agent"):
        st.session_state[k] = ""
    st.session_state.eval_date = None
    st.session_state.eval_result = None
    st.session_state.eval_error = None


def _evaluate() -> None:
    transcript = st.session_state.eval_transcript.strip()
    agent = st.session_state.eval_agent.strip()
    errors = []
    if len(transcript) < MIN_TRANSCRIPT_CHARS:
        errors.append(f"Paste a transcript of at least {MIN_TRANSCRIPT_CHARS} characters.")
    if not agent:
        errors.append("Enter the agent's name.")
    if errors:
        st.session_state.eval_error = " ".join(errors)
        return

    payload = {
        "transcript": transcript,
        "business_type": st.session_state.eval_business_type,
        "agent_name": agent,
        "call_date": st.session_state.eval_date.isoformat() if st.session_state.eval_date else None,
    }
    try:
        with st.spinner("Evaluating transcript…"):
            st.session_state.eval_result = api_client.create_evaluation(payload)
        st.session_state.eval_error = None
    except api_client.ApiError as exc:
        st.session_state.eval_error = str(exc)


def render() -> None:
    _init_state()
    st.title("Evaluate a call")
    st.caption(
        "Paste a sales-call transcript to score it against the QA rubric and generate a CRM note "
        "and follow-ups. Label turns with `Agent:` and `Customer:` for best results."
    )
    health = ui.mode_banner()

    with st.container(border=True):
        demo_row = st.container(horizontal=True, vertical_alignment="center")
        demo_row.markdown("**Load a demo transcript** (fictional):")
        for key, label in DEMO_BUTTONS.items():
            demo_row.button(label, key=f"demo_{key}", on_click=_load_demo, args=(key,), icon=":material/description:")

        st.text_area(
            "Transcript",
            key="eval_transcript",
            height=280,
            placeholder="Agent: Thank you for calling Summit Roofing, this is Maya…\nCustomer: Hi, we have a leak…",
        )
        st.file_uploader(
            "Or upload a transcript (.txt)",
            type=["txt"],
            key="eval_upload",
            on_change=_load_upload,
        )

        c1, c2, c3 = st.columns(3)
        c1.selectbox("Business type", [b.value for b in BusinessType], key="eval_business_type")
        c2.text_input("Agent name", key="eval_agent", placeholder="e.g. Maya Torres")
        c3.date_input("Call date (optional)", key="eval_date", format="YYYY-MM-DD", help="Defaults to today.")

        actions = st.container(horizontal=True)
        submitted = actions.button(
            "Evaluate call",
            type="primary",
            icon=":material/analytics:",
            disabled=health is None,
        )
        actions.button("Clear", on_click=_clear)

    if submitted:
        _evaluate()
    if st.session_state.eval_error:
        st.error(st.session_state.eval_error, icon=":material/error:")

    result = st.session_state.eval_result
    if result:
        st.divider()
        st.subheader("Evaluation result")
        render_result(result)
