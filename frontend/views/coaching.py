"""Coaching: recurring rubric gaps across calls, a team heatmap, and a focus plan per agent."""

from datetime import date, timedelta

import streamlit as st

from frontend import api_client, charts, ui

PERIODS = {"Last 7 days": 7, "Last 30 days": 30, "All time": None}
TEAM = "Whole team"
TOP_GAPS = 4


def _filters(agents: list[str]) -> dict:
    days = PERIODS[st.session_state.get("coach_period") or "Last 30 days"]
    filters = {"start_date": date.today() - timedelta(days=days - 1)} if days else {}
    agent = st.session_state.get("coach_agent", TEAM)
    if agent != TEAM and agent in agents:
        filters["agent_name"] = agent
    return filters


def _gap_card(gap: dict, total: int, threshold: int) -> None:
    from frontend import pages  # imported here: pages imports this module

    with st.container(border=True):
        st.markdown(f"**{gap['category']}**")
        st.markdown(
            f":red[**{gap['gap_calls']} of {total} calls**] ({gap['gap_rate']:.0f}%) scored "
            f"{threshold} / 5 or lower"
        )
        badges = st.container(horizontal=True)
        for a in gap["agents"]:
            badges.badge(f"{a['agent_name']} · {a['gap_calls']}", color="gray")
        st.html(f'<div class="cf-coach"><b>Coaching tip.</b> {gap["coaching_tip"]}</div>')
        with st.expander("Example calls"):
            for ex in gap["examples"]:
                when = date.fromisoformat(ex["call_date"]).strftime("%b %d")
                st.page_link(
                    pages.HISTORY,
                    label=f"{when} · {ex['agent_name']} · {ex['score']} / 5",
                    icon=":material/open_in_new:",
                    query_params={"id": ex["evaluation_id"]},
                )
                st.caption(ex["feedback"])


def _other_gaps(gaps: list[dict]) -> None:
    rows = [
        {
            "Category": g["category"],
            "Calls with gap": g["gap_calls"],
            "Share": g["gap_rate"],
            "Agents": ", ".join(a["agent_name"] for a in g["agents"]),
        }
        for g in gaps
    ]
    st.dataframe(
        rows,
        hide_index=True,
        column_config={"Share": st.column_config.NumberColumn(format="%.0f%%")},
    )


def _agent_plan(agent: dict) -> None:
    with st.container(border=True):
        name_col, score_col = st.columns([3, 1], vertical_alignment="center")
        name_col.markdown(f"#### {agent['agent_name']}")
        name_col.caption(f"{agent['calls']} call{'s' if agent['calls'] != 1 else ''} evaluated")
        avg = agent["average_score"]
        with score_col:
            st.html(
                f'<div style="text-align:right;font-size:1.6rem;font-weight:800;color:{ui.score_color(round(avg))}">'
                f'{avg:.0f}<small style="font-size:0.85rem;color:{ui.MUTED}"> / 100</small></div>'
            )
        if agent["focus_areas"]:
            st.markdown("**Focus on**")
            badges = st.container(horizontal=True)
            for area in agent["focus_areas"]:
                badges.badge(area, color="orange", icon=":material/target:")
            st.html(f'<div class="cf-coach">{agent["coaching_tip"]}</div>')
        else:
            st.markdown(":green[**No recurring gaps.**] Every rubric category averages 3 / 5 or better.")
        if agent["strongest_area"]:
            st.caption(f"Strength: {agent['strongest_area']}")


def render() -> None:
    head = st.container(horizontal=True, vertical_alignment="bottom")
    head.title("Coaching")
    head.space("stretch")
    head.segmented_control(
        "Period", list(PERIODS), default="Last 30 days", key="coach_period", label_visibility="collapsed"
    )
    st.caption("Where the team keeps losing points, and what each agent should work on next.")
    if ui.mode_banner() is None:
        return

    try:
        team = api_client.dashboard_analytics()
        agents = sorted(a["agent_name"] for a in team["calls_by_agent"])
        st.selectbox("Agent", [TEAM] + agents, key="coach_agent", width=280)
        insights = api_client.coaching_insights(**_filters(agents))
    except api_client.ApiError as exc:
        st.error(str(exc), icon=":material/error:")
        return

    total = insights["total_calls"]
    if total == 0:
        st.info(
            "No calls in this period. Evaluate a call, or load the demo data with `python -m scripts.seed_demo`.",
            icon=":material/inbox:",
        )
        return
    threshold = insights["gap_threshold"]

    st.subheader("Recurring gaps")
    gaps = insights["recurring_gaps"]
    if not gaps:
        st.success(
            f"No recurring gaps: no rubric category scored {threshold} / 5 or lower on more than one call.",
            icon=":material/check_circle:",
        )
    else:
        st.caption(
            f"Rubric categories scoring {threshold} / 5 or lower on at least two calls, most frequent first."
        )
        grid = st.columns(2)
        for i, gap in enumerate(gaps[:TOP_GAPS]):
            with grid[i % 2]:
                _gap_card(gap, total, threshold)
        if len(gaps) > TOP_GAPS:
            with st.expander(f"{len(gaps) - TOP_GAPS} more recurring gap{'s' if len(gaps) - TOP_GAPS != 1 else ''}"):
                _other_gaps(gaps[TOP_GAPS:])

    st.subheader("Rubric scores by agent")
    st.caption("Average score per rubric category (out of 5). Red cells are the coaching opportunities.")
    st.altair_chart(charts.rubric_heatmap(insights["agents"]), width="stretch")

    st.subheader("Coaching plan by agent")
    st.caption("Lowest average score first.")
    cols = st.columns(2)
    for i, agent in enumerate(insights["agents"]):
        with cols[i % 2]:
            _agent_plan(agent)
