
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
HISTORY_FILE = DATA_DIR / "interview_history.json"


def load_history():
    if not HISTORY_FILE.exists():
        return []

    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def save_interview(session_id, session):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    history = load_history()

    report = {
        "session_id": session_id,
        "role": session["role"],
        "questions_attempted": len(session["results"]),
        "results": session["results"],
    }

    results = report["results"]
    total_points = sum(
        item["evaluation"]["total_score"] for item in results
    )
    maximum_points = len(results) * 10

    report["total_points"] = total_points
    report["maximum_points"] = maximum_points
    report["overall_percentage"] = (
        round(total_points / maximum_points * 100, 2)
        if maximum_points else 0
    )

    history = [
        item for item in history
        if item.get("session_id") != session_id
    ]
    history.append(report)

    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)


def get_history():
    return load_history()


def get_saved_report(session_id):
    for report in load_history():
        if report.get("session_id") == session_id:
            return report

    return None
