"""Write every demo transcript to sample_calls/ as a .txt file, plus an index.

Run from the project root after changing app/seed_data.py:

    python -m scripts.export_sample_calls

The files are plain transcripts, ready for the Evaluate page's upload box.
"""

from pathlib import Path

from app.seed_data import SEED_CALLS
from app.services.mock_evaluator import evaluate_transcript_mock

OUT_DIR = Path(__file__).resolve().parents[1] / "sample_calls"


def file_name(call: dict) -> str:
    return f"{call['key']}.txt"


def index_markdown() -> str:
    lines = [
        "# Sample call transcripts",
        "",
        "Fictional transcripts for trying the app. Upload one on the **Evaluate call** page,",
        "then set the business type and agent name shown below (the files contain only the transcript).",
        "",
        "All people, companies, addresses, phone numbers (555-01xx), and emails (example.com) are invented.",
        "",
        "Generated from `app/seed_data.py` by `python -m scripts.export_sample_calls`; edit the source, not these files.",
        "",
        "| File | Agent | Business type | Scenario | Mock score |",
        "|---|---|---|---|---|",
    ]
    for call in SEED_CALLS:
        score = evaluate_transcript_mock(call["transcript"], call["business_type"], call["agent_name"]).overall_score
        scenario = call["label"].split(": ", 1)[-1]
        lines.append(
            f"| [`{file_name(call)}`]({file_name(call)}) | {call['agent_name']} | "
            f"{call['business_type'].value} | {scenario} | {score} |"
        )
    return "\n".join(lines) + "\n"


def expected_files() -> dict[str, str]:
    files = {file_name(c): c["transcript"].strip() + "\n" for c in SEED_CALLS}
    files["README.md"] = index_markdown()
    return files


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for name, content in expected_files().items():
        (OUT_DIR / name).write_text(content)
    print(f"Wrote {len(SEED_CALLS)} transcripts and README.md to {OUT_DIR}")


if __name__ == "__main__":
    main()
