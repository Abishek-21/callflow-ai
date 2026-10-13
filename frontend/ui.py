"""Shared UI helpers: styling, status banners, small cards, and copy buttons."""

import html
import json

import pandas as pd
import streamlit as st

from frontend import api_client

NAVY = "#0B2545"
INK = "#10223A"
MUTED = "#5B6B80"
BORDER = "#DCE3EC"
GREEN = "#1E8E5A"
AMBER = "#C98A0B"
RED = "#C0392B"

CSS = f"""
<style>
.cf-card {{
  border: 1px solid {BORDER}; border-radius: 10px; padding: 14px 16px;
  background: #fff; min-height: 104px;
}}
.cf-label {{
  font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
  color: {MUTED}; margin-bottom: 6px; font-weight: 600;
}}
.cf-value {{ font-size: 1.3rem; font-weight: 700; color: {INK}; line-height: 1.25; }}
.cf-sub {{ font-size: 0.85rem; color: {MUTED}; margin-top: 4px; }}
.cf-score {{ font-size: 2.6rem; font-weight: 800; line-height: 1; }}
.cf-score small {{ font-size: 1rem; color: {MUTED}; font-weight: 600; }}
.cf-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 7px; vertical-align: 1px; }}
.cf-coach {{
  border-left: 4px solid {GREEN}; background: #EEF8F3; padding: 12px 16px;
  border-radius: 6px; color: {INK};
}}
.cf-brand {{ font-size: 1.35rem; font-weight: 800; letter-spacing: 0.02em; color: #fff; }}
.cf-brand span {{ color: #5FD3A0; }}
.cf-tagline {{ font-size: 0.8rem; color: #A9B8CC; margin-top: -4px; }}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def score_color(score: int) -> str:
    if score >= 80:
        return GREEN
    if score >= 60:
        return AMBER
    return RED


def score_band(score: int) -> str:
    if score >= 80:
        return "Strong call"
    if score >= 60:
        return "Needs coaching"
    return "At risk"


TEMPERATURE_COLORS = {"Hot": RED, "Warm": AMBER, "Cold": "#4F7CAC"}
URGENCY_COLORS = {"High": RED, "Medium": AMBER, "Low": GREEN}


def card(label: str, value: str, sub: str = "", dot_color: str | None = None) -> None:
    dot = f'<span class="cf-dot" style="background:{dot_color}"></span>' if dot_color else ""
    sub_html = f'<div class="cf-sub">{html.escape(sub)}</div>' if sub else ""
    st.html(
        f'<div class="cf-card"><div class="cf-label">{html.escape(label)}</div>'
        f'<div class="cf-value">{dot}{html.escape(value)}</div>{sub_html}</div>'
    )


def score_card(score: int) -> None:
    color = score_color(score)
    st.html(
        f'<div class="cf-card"><div class="cf-label">Quality score</div>'
        f'<div class="cf-score" style="color:{color}">{score}<small> / 100</small></div>'
        f'<div class="cf-sub">{score_band(score)}</div></div>'
    )


def copy_button(text: str, label: str) -> None:
    """A button that copies `text` to the clipboard (falls back to execCommand).

    `text` may contain LLM output, so it is embedded only as a JSON string with every
    "<" escaped; it can't close the <script> tag or inject markup.
    """
    payload = json.dumps(text).replace("<", "\\u003c")
    st.iframe(
        f"""
<button id="copy">{html.escape(label)}</button>
<style>
  body {{ margin: 0; font-family: "Source Sans Pro", "Source Sans 3", system-ui, sans-serif; }}
  button {{
    font: inherit; font-size: 0.95rem; color: {INK}; background: #fff; cursor: pointer;
    border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 14px;
  }}
  button:hover {{ border-color: {GREEN}; color: {GREEN}; }}
</style>
<script>
  const text = {payload};
  const btn = document.getElementById("copy");
  const label = btn.textContent;
  btn.addEventListener("click", async () => {{
    let ok = false;
    try {{
      await navigator.clipboard.writeText(text);
      ok = true;
    }} catch (e) {{
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try {{ ok = document.execCommand("copy"); }} catch (e2) {{}}
      ta.remove();
    }}
    btn.textContent = ok ? "✓ Copied" : "Copy failed: select the text and copy manually";
    setTimeout(() => (btn.textContent = label), 2000);
  }});
</script>
""",
        height=42,
    )


@st.cache_data(ttl=10, show_spinner=False)
def backend_health() -> dict | None:
    return api_client.health()


def sidebar_status() -> None:
    with st.sidebar:
        health = backend_health()
        if health is None:
            st.markdown(":red[**API offline**]")
        elif health["evaluation_mode"] == "mock":
            st.markdown(":orange[**Mock evaluation mode**]")
        else:
            st.markdown(f":green[**AI evaluation**]  \n{health['provider']} · `{health['model']}`")
        st.caption(
            "Portfolio prototype. All customers, agents, companies, and calls are fictional."
        )


def mode_banner() -> dict | None:
    """Explain how evaluations are being produced. Returns backend health (None if offline)."""
    health = backend_health()
    if health is None:
        st.error(
            f"Can't reach the CallFlow API at `{api_client.API_BASE_URL}`. "
            "Start it in another terminal with `uvicorn app.main:app --reload`, then refresh.",
            icon=":material/cloud_off:",
        )
    elif health["evaluation_mode"] == "mock":
        st.info(
            "**Mock evaluation mode.** No LLM API key is configured, so calls are scored by a "
            "deterministic, rule-based evaluator. Add `OPENAI_API_KEY` to `.env` (OpenAI, or an "
            "OpenAI-compatible provider such as Groq) for AI evaluation.",
            icon=":material/science:",
        )
    return health


def calls_table(rows: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Evaluation summaries as a display table, plus its column config."""
    df = pd.DataFrame(
        [
            {
                "ID": r["id"],
                "Date": r["call_date"],
                "Agent": r["agent_name"],
                "Customer": r["customer_name"] or "Unknown",
                "Service": r["service_type"],
                "Lead": r["lead_temperature"],
                "Urgency": r["urgency"],
                "Booked": r["appointment_booked"],
                "Score": r["overall_score"],
                "Mode": "AI" if r["evaluation_mode"] == "llm" else "Mock",
            }
            for r in rows
        ]
    )
    config = {
        "ID": st.column_config.NumberColumn(width="small", format="%d"),
        "Date": st.column_config.DateColumn(format="MMM D, YYYY"),
        "Booked": st.column_config.CheckboxColumn(),
        "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d", color="green"),
        "Mode": st.column_config.TextColumn(width="small"),
    }
    return df, config
