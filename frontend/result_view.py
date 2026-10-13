"""Renders one evaluation: scorecard, CRM record, editable follow-ups, transcript.

Shared by the Evaluate page and (later) the call-history detail view.
"""

from datetime import date

import pandas as pd
import streamlit as st

from app.schemas import LeadTemperature, follow_up_timing
from frontend import ui


def _split_label(item: str) -> tuple[str, str]:
    """'Category: feedback' -> ('Category', 'feedback')."""
    head, sep, tail = item.partition(": ")
    return (head, tail) if sep else ("", item)


def _bullets(items: list[str], empty: str) -> None:
    if not items:
        st.caption(empty)
        return
    lines = []
    for item in items:
        head, tail = _split_label(item)
        lines.append(f"- **{head}:** {tail}" if head else f"- {tail}")
    st.markdown("\n".join(lines))


def _appointment_text(r: dict) -> tuple[str, str]:
    if r["appointment_booked"]:
        return "Booked", r["appointment_time"] or "Time not captured"
    return "Not booked", ""


def render_result(r: dict) -> None:
    key = f"r{r['id']}"  # widget keys are per evaluation, so edits reset on a new result
    timing = follow_up_timing(LeadTemperature(r["lead_temperature"]), r["appointment_booked"])

    if r.get("notice"):
        st.warning(r["notice"], icon=":material/info:")

    # --- Meta line -----------------------------------------------------------
    call_date = date.fromisoformat(r["call_date"]).strftime("%b %d, %Y")
    meta = st.container(horizontal=True, vertical_alignment="center")
    meta.markdown(f"**{r['agent_name']}** · {r['business_type']} · {call_date} · Evaluation #{r['id']}")
    if r["evaluation_mode"] == "mock":
        meta.badge("Mock evaluation", icon=":material/science:", color="orange")
    else:
        meta.badge("AI evaluation", icon=":material/auto_awesome:", color="green")
    meta.badge("Fictional data", color="gray")

    # --- Headline cards ----------------------------------------------------------
    cols = st.columns([1.2, 1, 1, 1.2, 1.4])
    with cols[0]:
        ui.score_card(r["overall_score"])
    with cols[1]:
        ui.card("Lead", r["lead_temperature"], dot_color=ui.TEMPERATURE_COLORS[r["lead_temperature"]])
    with cols[2]:
        ui.card("Urgency", r["urgency"], dot_color=ui.URGENCY_COLORS[r["urgency"]])
    with cols[3]:
        status, when = _appointment_text(r)
        ui.card("Appointment", status, when, dot_color=ui.GREEN if r["appointment_booked"] else ui.MUTED)
    with cols[4]:
        ui.card("Follow up", timing)

    if r["risk_flags"]:
        st.warning("**Risk flags**\n" + "\n".join(f"- {f}" for f in r["risk_flags"]), icon=":material/flag:")

    scorecard, crm, followups, transcript = st.tabs(["Scorecard", "CRM record", "Follow-ups", "Transcript"])

    # --- Scorecard ---------------------------------------------------------------
    with scorecard:
        rubric = pd.DataFrame(r["rubric_scores"]).rename(
            columns={"category": "Category", "score": "Score", "feedback": "Feedback"}
        )
        st.dataframe(
            rubric,
            hide_index=True,
            column_config={
                "Category": st.column_config.TextColumn(width="medium"),
                "Score": st.column_config.ProgressColumn(
                    min_value=0, max_value=5, format="%d / 5", width="small", color="green"
                ),
                "Feedback": st.column_config.TextColumn(width="large"),
            },
        )
        st.html(f'<div class="cf-coach"><b>Coaching recommendation.</b> {r["coaching_recommendation"]}</div>')
        left, right = st.columns(2)
        with left:
            st.markdown("##### :green[:material/check_circle:] Strengths")
            _bullets(r["strengths"], "No category scored 4 or higher.")
        with right:
            st.markdown("##### :orange[:material/error:] Missed opportunities")
            _bullets(r["missed_opportunities"], "No category scored 2 or lower.")

    # --- CRM record ------------------------------------------------------------------
    with crm:
        details, note = st.columns([1, 1.2], gap="large")
        with details:
            status, when = _appointment_text(r)
            rows = {
                "Customer": r["customer_name"] or "Not captured",
                "Phone": r["customer_phone"] or "Not captured",
                "Email": r["customer_email"] or "Not captured",
                "Location": r["location"] or "Not captured",
                "Service type": r["service_type"],
                "Problem": r["customer_problem"],
                "Urgency": r["urgency"],
                "Lead temperature": r["lead_temperature"],
                "Appointment": f"{status} ({when})" if when else status,
                "Follow-up timing": timing,
                "Next action": r["recommended_next_action"],
            }
            st.markdown("\n".join(f"**{k}:** {v}  " for k, v in rows.items()))
        with note:
            crm_note = st.text_area("CRM note", r["crm_note"], height=210, key=f"{key}_crm")
            ui.copy_button(crm_note, "Copy CRM note")
            st.caption("Edits are for copying only; they aren't saved.")

    # --- Follow-ups --------------------------------------------------------------------
    with followups:
        sms_col, email_col = st.columns([1, 1.4], gap="large")
        with sms_col:
            sms = st.text_area("SMS", r["sms_follow_up"], height=160, key=f"{key}_sms")
            segments = max(1, -(-len(sms) // 160))
            st.caption(f"{len(sms)} characters · {segments} SMS segment{'s' if segments > 1 else ''}")
            ui.copy_button(sms, "Copy SMS")
        with email_col:
            subject = st.text_input("Email subject", r["email_subject"], key=f"{key}_subject")
            body = st.text_area("Email body", r["email_follow_up"], height=300, key=f"{key}_email")
            ui.copy_button(f"Subject: {subject}\n\n{body}", "Copy email")
        st.caption("Edits are for copying only; they aren't saved.")

    # --- Transcript ------------------------------------------------------------------------
    with transcript:
        st.code(r["transcript"], language=None, wrap_lines=True)
