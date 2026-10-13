"""Dashboard: headline metrics, trend and breakdown charts, agent performance, and recent calls."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from frontend import api_client, charts, ui

PERIODS = {"Last 7 days": 7, "Last 30 days": 30, "All time": None}
RECENT_LIMIT = 10


def _period_filters() -> dict:
    days = PERIODS[st.session_state.get("dash_period") or "Last 30 days"]
    return {"start_date": date.today() - timedelta(days=days - 1)} if days else {}


def _kpis(m: dict) -> None:
    cols = st.columns(5)
    with cols[0]:
        ui.card("Calls evaluated", str(m["total_calls"]))
    with cols[1]:
        avg = m["average_score"]
        if avg is None:
            ui.card("Average score", "–")
        else:
            ui.card(
                "Average score",
                f"{avg:.0f} / 100",
                f"{m['low_score_calls']} call{'s' if m['low_score_calls'] != 1 else ''} under 60",
                dot_color=ui.score_color(round(avg)),
            )
    with cols[2]:
        ui.card("Hot leads", str(m["hot_leads"]), dot_color=ui.TEMPERATURE_COLORS["Hot"])
    with cols[3]:
        rate = m["booking_rate"]
        ui.card(
            "Appointments booked",
            str(m["appointments_booked"]),
            f"{rate:.0f}% booking rate" if rate is not None else "",
            dot_color=ui.GREEN,
        )
    with cols[4]:
        ui.card("Follow-ups needed", str(m["follow_ups_needed"]), "Hot or warm leads not yet booked", dot_color=ui.AMBER)


def _agent_table(agents: list[dict]) -> None:
    df = pd.DataFrame(agents).rename(
        columns={
            "agent_name": "Agent",
            "calls": "Calls",
            "average_score": "Avg score",
            "appointments_booked": "Booked",
            "booking_rate": "Booking rate",
        }
    )
    st.dataframe(
        df,
        hide_index=True,
        column_config={
            "Avg score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f", color="green"),
            "Booking rate": st.column_config.NumberColumn(format="%.0f%%"),
        },
    )


def _recent_calls(filters: dict) -> None:
    rows = api_client.list_evaluations(**filters, limit=RECENT_LIMIT)
    df, config = ui.calls_table(rows)
    event = st.dataframe(
        df,
        key="dash_recent",
        hide_index=True,
        column_config=config,
        column_order=["Date", "Agent", "Customer", "Service", "Lead", "Booked", "Score", "Mode"],
        on_select="rerun",
        selection_mode="single-row",
    )
    if event.selection.rows:
        from frontend import pages  # imported here: pages imports this module

        st.switch_page(pages.HISTORY, query_params={"id": rows[event.selection.rows[0]]["id"]})


def render() -> None:
    head = st.container(horizontal=True, vertical_alignment="bottom")
    head.title("Dashboard")
    head.space("stretch")
    head.segmented_control("Period", list(PERIODS), default="Last 30 days", key="dash_period", label_visibility="collapsed")
    st.caption("Call quality and lead follow-up at a glance. Select a recent call to open its full evaluation.")
    if ui.mode_banner() is None:
        return

    filters = _period_filters()
    try:
        metrics = api_client.dashboard_metrics(**filters)
        if metrics["total_calls"] == 0:
            st.info(
                "No calls in this period. Evaluate a call, or load the demo data with "
                "`python -m scripts.seed_demo`.",
                icon=":material/inbox:",
            )
            return
        analytics = api_client.dashboard_analytics(**filters)
        _kpis(metrics)

        trend, leads = st.columns([1.8, 1], gap="large")
        with trend:
            st.subheader("Score trend")
            st.altair_chart(charts.score_trend(analytics["score_trend"]), width="stretch")
            st.caption("Line: 7-day rolling average. Dots: each day's average (larger = more calls). "
                       "Dashed lines mark 80 (strong call) and 60 (needs coaching).")
        with leads:
            st.subheader("Lead temperature")
            st.altair_chart(charts.lead_temperature(analytics["lead_temperature_distribution"]), width="stretch")

        services, agents = st.columns([1, 1], gap="large")
        with services:
            st.subheader("Calls by service type")
            st.altair_chart(charts.calls_by_service(analytics["calls_by_service_type"]), width="stretch")
        with agents:
            st.subheader("Agent performance")
            _agent_table(analytics["calls_by_agent"])

        st.subheader("Recent calls")
        _recent_calls(filters)
    except api_client.ApiError as exc:
        st.error(str(exc), icon=":material/error:")
