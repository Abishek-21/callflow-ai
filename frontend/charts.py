"""Altair charts for the dashboard and coaching pages, in the app's colours."""

import altair as alt
import pandas as pd

from app.schemas import LeadTemperature, RubricCategory
from frontend import ui

NAVY = "#12355B"

# Short axis labels for the rubric heatmap.
SHORT_LABELS = {
    RubricCategory.OPENING_RAPPORT: "Opening",
    RubricCategory.LEAD_QUALIFICATION: "Qualification",
    RubricCategory.PROBLEM_DISCOVERY: "Discovery",
    RubricCategory.SERVICE_AREA_URGENCY: "Area & urgency",
    RubricCategory.VALUE_COMMUNICATION: "Value",
    RubricCategory.OBJECTION_HANDLING: "Objections",
    RubricCategory.APPOINTMENT_ATTEMPT: "Booking ask",
    RubricCategory.CLEAR_NEXT_STEP: "Next step",
    RubricCategory.PROFESSIONAL_COMMUNICATION: "Professionalism",
}


ROLLING_DAYS = 7


def _rolling_average(points: list[dict], days: int = ROLLING_DAYS) -> pd.DataFrame:
    """Call-weighted trailing average over `days` calendar days, on each date that had calls."""
    df = pd.DataFrame(points)
    df["call_date"] = pd.to_datetime(df["call_date"])
    df["total"] = df["average_score"] * df["calls"]
    daily = df.set_index("call_date")[["total", "calls"]].asfreq("D", fill_value=0)
    window = daily.rolling(f"{days}D").sum()
    df["rolling_average"] = (window["total"] / window["calls"]).reindex(df["call_date"]).to_numpy()
    return df


def score_trend(points: list[dict], height: int = 260) -> alt.Chart:
    """Daily average score (dots) with a 7-day rolling average (line); 80 and 60 bands marked."""
    df = _rolling_average(points)
    x = alt.X("call_date:T", title=None, axis=alt.Axis(format="%b %d", labelAngle=0, tickCount="day"))
    y_scale = alt.Scale(domain=[0, 100])
    tooltip = [
        alt.Tooltip("call_date:T", title="Date", format="%b %d, %Y"),
        alt.Tooltip("calls:Q", title="Calls"),
        alt.Tooltip("average_score:Q", title="Day average", format=".0f"),
        alt.Tooltip("rolling_average:Q", title=f"{ROLLING_DAYS}-day average", format=".0f"),
    ]
    base = alt.Chart(df).encode(x=x, tooltip=tooltip)
    dots = base.mark_circle(color=NAVY, opacity=0.35).encode(
        y=alt.Y("average_score:Q", title="Score", scale=y_scale),
        size=alt.Size("calls:Q", legend=None, scale=alt.Scale(range=[50, 200])),
    )
    line = base.mark_line(color=NAVY, strokeWidth=3, interpolate="monotone").encode(
        y=alt.Y("rolling_average:Q", scale=y_scale)
    )
    bands = pd.DataFrame({"y": [80, 60], "color": [ui.GREEN, ui.AMBER]})
    rules = (
        alt.Chart(bands)
        .mark_rule(strokeDash=[4, 4], opacity=0.6)
        .encode(y="y:Q", color=alt.Color("color:N", scale=None, legend=None))
    )
    return (rules + dots + line).properties(height=height)


def calls_by_service(services: list[dict], height: int = 260) -> alt.Chart:
    df = pd.DataFrame(services)
    whole_numbers = list(range(int(df["calls"].max()) + 1))
    return (
        alt.Chart(df)
        .mark_bar(color=NAVY, cornerRadiusEnd=3)
        .encode(
            x=alt.X("calls:Q", title="Calls", axis=alt.Axis(values=whole_numbers, format="d")),
            y=alt.Y("service_type:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("service_type:N", title="Service"),
                alt.Tooltip("calls:Q", title="Calls"),
                alt.Tooltip("average_score:Q", title="Average score", format=".0f"),
            ],
        )
        .properties(height=height)
    )


def lead_temperature(distribution: list[dict], height: int = 260) -> alt.Chart:
    counts = {d["lead_temperature"]: d["calls"] for d in distribution}
    order = [t.value for t in LeadTemperature]
    labels = [f"{t} ({counts.get(t, 0)})" for t in order]
    df = pd.DataFrame({"label": labels, "lead_temperature": order, "calls": [counts.get(t, 0) for t in order]})
    return (
        alt.Chart(df)
        .mark_arc(innerRadius=60, stroke="#fff")
        .encode(
            theta=alt.Theta("calls:Q", stack=True),
            color=alt.Color(
                "label:N",
                title=None,
                sort=labels,
                scale=alt.Scale(domain=labels, range=[ui.TEMPERATURE_COLORS[t] for t in order]),
                legend=alt.Legend(orient="bottom"),
            ),
            order=alt.Order("rank:Q"),
            tooltip=[alt.Tooltip("lead_temperature:N", title="Lead"), alt.Tooltip("calls:Q", title="Calls")],
        )
        .transform_window(rank="row_number()")
        .properties(height=height)
    )


def rubric_heatmap(agents: list[dict]) -> alt.Chart:
    """Agents x rubric categories, coloured by average category score (0-5)."""
    rows = [
        {
            "agent": a["agent_name"],
            "category": SHORT_LABELS[RubricCategory(s["category"])],
            "full_category": s["category"],
            "score": s["average_score"],
        }
        for a in agents
        for s in a["category_scores"]
    ]
    df = pd.DataFrame(rows)
    x = alt.X("category:N", title=None, sort=list(SHORT_LABELS.values()), axis=alt.Axis(labelAngle=-30, orient="top"))
    y = alt.Y("agent:N", title=None, sort=[a["agent_name"] for a in agents])
    cells = (
        alt.Chart(df)
        .mark_rect(cornerRadius=3, stroke="#fff", strokeWidth=2)
        .encode(
            x=x,
            y=y,
            color=alt.Color(
                "score:Q",
                title="Avg / 5",
                scale=alt.Scale(domain=[0, 2.5, 5], range=[ui.RED, ui.AMBER, ui.GREEN]),
            ),
            tooltip=[
                alt.Tooltip("agent:N", title="Agent"),
                alt.Tooltip("full_category:N", title="Category"),
                alt.Tooltip("score:Q", title="Average", format=".1f"),
            ],
        )
    )
    labels = (
        alt.Chart(df)
        .mark_text(color="#fff", fontWeight="bold")
        .encode(x=x, y=y, text=alt.Text("score:Q", format=".1f"))
    )
    return (cells + labels).properties(height=max(120, 46 * len(agents)))
