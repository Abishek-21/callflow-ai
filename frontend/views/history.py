"""Call history: filter past evaluations and open any call's full evaluation.

The open call is kept in the URL (?id=12), so a call can be linked to directly,
including from the dashboard's recent-calls table.
"""

import streamlit as st

from app.schemas import LeadTemperature
from frontend import api_client, ui
from frontend.result_view import render_result

ALL = "All"
BOOKED_OPTIONS = {ALL: None, "Booked": True, "Not booked": False}
FILTER_KEYS = ("hist_dates", "hist_agent", "hist_service", "hist_lead", "hist_booked", "hist_min_score")


def _init_state() -> None:
    st.session_state.setdefault("hist_agent", ALL)
    st.session_state.setdefault("hist_service", ALL)
    st.session_state.setdefault("hist_lead", ALL)
    st.session_state.setdefault("hist_booked", ALL)
    st.session_state.setdefault("hist_min_score", 0)
    st.session_state.setdefault("hist_ids", [])


def _reset_filters() -> None:
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)
    _init_state()


def _on_select() -> None:
    rows = st.session_state.hist_table.selection.rows
    if rows:
        st.query_params["id"] = str(st.session_state.hist_ids[rows[0]])
    else:
        st.query_params.pop("id", None)


def _close_detail() -> None:
    st.query_params.pop("id", None)


def _filters() -> dict:
    s = st.session_state
    dates = s.get("hist_dates") or ()
    return {
        "start_date": dates[0] if len(dates) > 0 else None,
        "end_date": dates[1] if len(dates) > 1 else None,
        "agent_name": None if s.hist_agent == ALL else s.hist_agent,
        "service_type": None if s.hist_service == ALL else s.hist_service,
        "lead_temperature": None if s.hist_lead == ALL else s.hist_lead,
        "appointment_booked": BOOKED_OPTIONS[s.hist_booked],
        "min_score": s.hist_min_score or None,
    }


def _filter_bar(options: dict) -> None:
    agents = [ALL] + sorted(a["agent_name"] for a in options["calls_by_agent"])
    services = [ALL] + sorted(s["service_type"] for s in options["calls_by_service_type"])
    # A saved choice can disappear from the options (e.g. after reseeding); fall back to All.
    for key, choices in (("hist_agent", agents), ("hist_service", services)):
        if st.session_state[key] not in choices:
            st.session_state[key] = ALL

    with st.container(border=True):
        c1, c2, c3 = st.columns([1.3, 1, 1])
        # value=() makes this a range picker; set here (not via session state) so Reset restores it.
        c1.date_input("Call date range", value=(), key="hist_dates", format="YYYY-MM-DD")
        c2.selectbox("Agent", agents, key="hist_agent")
        c3.selectbox("Service type", services, key="hist_service")
        c4, c5, c6, c7 = st.columns([1, 1, 1.3, 0.7], vertical_alignment="bottom")
        c4.selectbox("Lead temperature", [ALL] + [t.value for t in LeadTemperature], key="hist_lead")
        c5.selectbox("Appointment", list(BOOKED_OPTIONS), key="hist_booked")
        c6.slider("Minimum score", 0, 100, step=5, key="hist_min_score")
        c7.button("Reset", on_click=_reset_filters, icon=":material/restart_alt:", width="stretch")


def _selected_id() -> int | None:
    raw = st.query_params.get("id")
    return int(raw) if raw and raw.isdigit() else None


def _render_detail(evaluation_id: int) -> None:
    st.divider()
    header = st.container(horizontal=True, vertical_alignment="center")
    header.subheader(f"Call #{evaluation_id}")
    header.button("Close", on_click=_close_detail, icon=":material/close:")
    try:
        evaluation = api_client.get_evaluation(evaluation_id)
    except api_client.ApiError as exc:
        st.warning(str(exc), icon=":material/search_off:")
        return
    render_result(evaluation)


def render() -> None:
    _init_state()
    st.title("Call history")
    st.caption("Filter past evaluations and select a row to open the full scorecard, CRM record, and follow-ups.")
    if ui.mode_banner() is None:
        return

    try:
        options = api_client.dashboard_analytics()
        _filter_bar(options)
        rows = api_client.list_evaluations(**_filters(), limit=500)
    except api_client.ApiError as exc:
        st.error(str(exc), icon=":material/error:")
        return

    selected = _selected_id()
    if not rows:
        st.session_state.hist_ids = []
        if options["calls_by_agent"]:
            st.info("No calls match these filters.", icon=":material/filter_alt_off:")
        else:
            st.info(
                "No calls evaluated yet. Evaluate a call, or load the demo data with "
                "`python -m scripts.seed_demo`.",
                icon=":material/inbox:",
            )
    else:
        st.session_state.hist_ids = [r["id"] for r in rows]
        count = f"{len(rows)} call{'s' if len(rows) != 1 else ''}"
        average = round(sum(r["overall_score"] for r in rows) / len(rows))
        st.caption(f"**{count}** · average score **{average}** · newest first")
        df, config = ui.calls_table(rows)
        st.dataframe(
            df,
            key="hist_table",
            hide_index=True,
            column_config=config,
            on_select=_on_select,
            selection_mode="single-row",
            height=min(38 + 35 * len(df), 420),
        )

    if selected is not None:
        _render_detail(selected)
