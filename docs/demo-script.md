# Demo video script (about 3 minutes)

A short walkthrough for a portfolio or a recruiter. Show the workflow, not every feature.

## Before recording

- [ ] Reset to clean demo data: `python -m scripts.seed_demo --reset`
- [ ] Decide which mode you're showing and say it on camera:
  - **AI mode:** key set in `.env`; the sidebar shows "AI evaluation · Groq · …". Free tiers allow about two evaluations a minute, so evaluate only once during the take. Wait a minute after any practice run.
  - **Mock mode:** no key; the sidebar shows "Mock evaluation mode".
- [ ] Start both servers: `uvicorn app.main:app` and `streamlit run frontend/streamlit_app.py`
- [ ] Browser:
  - one window at about 1440×900
  - zoom 100–110%
  - bookmarks bar hidden
  - other tabs closed
- [ ] Turn on macOS Do Not Disturb so notifications don't appear.
- [ ] Open tabs in order: http://localhost:8501 (Evaluate), then http://localhost:8000/docs

**Recording:** press `Cmd + Shift + 5` and choose **Record Selected Portion** (built into macOS), or use QuickTime or Loom. Speak over the recording, or record silently and add captions.

## Script

| Time | Screen | Say (roughly) |
|---|---|---|
| 0:00 | Evaluate page | "This is CallFlow AI, a portfolio prototype I built that reviews sales calls for a home-services call center. All the data here is fictional." |
| 0:15 | Click **HVAC · weak call**, then **Evaluate call** | "A manager pastes a transcript, or loads one. Here an agent takes a call about a broken AC with a newborn in the house." |
| 0:30 | Scorecard tab | "The call is scored on nine rubric categories. This one scores low: few discovery questions, and the agent never asked for the appointment. It gets a coaching recommendation and risk flags, like an urgent lead that wasn't booked." |
| 0:55 | Point at the badge | "This was evaluated by an LLM with structured output. Every result is validated against a schema, and if the API fails it falls back to a rule-based evaluator and says so." |
| 1:10 | **CRM record** tab, then **Copy CRM note** | "It extracts a CRM-ready record. It leaves blank anything the customer didn't say, rather than inventing it." |
| 1:25 | **Follow-ups** tab, edit a word in the SMS, then **Copy SMS** | "It drafts an SMS and an email. They're editable drafts; nothing is sent automatically." |
| 1:40 | **Dashboard** | "Every evaluation is stored. The dashboard shows volume, average score, hot leads, bookings and follow-ups still needed, plus the score trend and the lead mix." |
| 2:00 | Click a row in **Recent calls** | "Any call opens in full from here or from Call history, which has filters for agent, service, lead temperature and score." |
| 2:15 | **Coaching** | "Because rubric scores are stored per category, the coaching page can find recurring gaps: here, qualification and value communication, and which agents they affect. The heatmap shows it at a glance." |
| 2:35 | Coaching plan cards | "Each agent gets up to three focus areas and a concrete tip." |
| 2:45 | API docs tab | "It's a FastAPI backend with a Streamlit front end, documented API endpoints, and 103 tests." |
| 2:55 | Back to the dashboard | "The idea: start from the operational workflow, make the AI output structured and reviewable, then connect it to follow-up and reporting. Thanks for watching." |

## After recording

- Trim the start and end. QuickTime: `Cmd + T`.
- Upload to YouTube as **Unlisted**, or to Loom, and add the link near the top of the README:
  `**Demo video:** https://...`
- Take screenshots with `Cmd + Shift + 4`, then `Space`, then click the window. Save them using the file names listed in the README's Screenshots section, in `docs/screenshots/`.
