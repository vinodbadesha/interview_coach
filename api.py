
import json
import time
import os
import tempfile
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from storage import save_interview, get_history, get_saved_report

from analyze import analyze_resume
from questions_gen import build_session
from evaluator import score_answer


app = FastAPI(title="AI Interview Practice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Prototype storage: sessions exist only while this server is running.
sessions = {}


class StartRequest(BaseModel):
    session_id: str


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


def get_session(session_id):
    session = sessions.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return session


def public_question(question, index, total):
    # Never send the scoring key points to the frontend.
    return {
        "question_number": index + 1,
        "total_questions": total,
        "category": question.get("category", "General"),
        "question": question["question"],
    }


@app.get("/")
def home():
    return {
        "message": "AI Interview Practice API is running."
    }


@app.post("/prepare")
async def prepare_interview(
    role: str = Form(...),
    resume: UploadFile = File(...),
):
    role = role.strip()

    if not role:
        raise HTTPException(status_code=400, detail="Role is required.")

    filename = resume.filename or ""

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF resume.",
        )

    # Basic upload-size limit: 5 MB.
    content = await resume.read(5 * 1024 * 1024 + 1)

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Resume must be 5 MB or smaller.",
        )

    if not content:
        raise HTTPException(status_code=400, detail="Resume is empty.")

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        ) as temp:
            temp.write(content)
            temp_path = temp.name

        # Reuse your existing resume analysis and question generation.
        start = time.perf_counter()
        print("Starting resume analysis...", flush=True)

        resume_data = analyze_resume(temp_path)

        print(
            f"Resume analysis took {time.perf_counter() - start:.2f} seconds",
            flush=True
        )

        start = time.perf_counter()
        print("Starting question generation...", flush=True)

        questions = build_session(role, resume_data, n_bank=10, n_resume=5)

        print(
            f"Question generation took {time.perf_counter() - start:.2f} seconds",
            flush=True
        )

        if not questions:
            raise HTTPException(
                status_code=422,
                detail="No interview questions could be generated.",
            )

        session_id = str(uuid.uuid4())

        sessions[session_id] = {
            "role": role,
            "questions": questions,
            "current_index": 0,
            "started": False,
            "ended": False,
            "results": [],
        }

        return {
            "session_id": session_id,
            "role": role,
            "total_questions": len(questions),
            "message": "Interview prepared. Start when you are ready.",
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not prepare interview: {error}",
        ) from error

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/start")
def start_interview(request: StartRequest):
    session = get_session(request.session_id)

    if session["started"]:
        raise HTTPException(
            status_code=409,
            detail="Interview has already started.",
        )

    session["started"] = True

    question = session["questions"][0]

    return {
        "status": "started",
        "question": public_question(
            question,
            0,
            len(session["questions"]),
        ),
    }


@app.post("/answer")
def submit_answer(request: AnswerRequest):
    session = get_session(request.session_id)

    if session.get("ended", False):
        raise HTTPException(
            status_code=409,
            detail="This interview has ended.",
        )

    if not session["started"]:
        raise HTTPException(
            status_code=409,
            detail="Start the interview before submitting an answer.",
        )

    answer = request.answer.strip()

    if not answer:
        raise HTTPException(
            status_code=400,
            detail="Answer cannot be empty.",
        )

    index = session["current_index"]
    questions = session["questions"]

    if index >= len(questions):
        raise HTTPException(
            status_code=409,
            detail="Interview is already complete.",
        )

    question = questions[index]

    try:
        evaluation = score_answer(
            question,
            answer,
            session["role"],
        )
    except Exception as error:
        # Do not advance the question if evaluation fails.
        raise HTTPException(
            status_code=502,
            detail="Answer evaluation failed. Please retry.",
        ) from error

    session["results"].append({
        "question_number": index + 1,
        "category": question.get("category", "General"),
        "question": question["question"],
        "answer": answer,
        "evaluation": evaluation,
    })

    session["current_index"] += 1

    next_index = session["current_index"]

    if next_index < len(questions):
        next_question = public_question(
            questions[next_index],
            next_index,
            len(questions),
        )
    else:
        next_question = None

    completed = next_question is None

    if completed:
        save_interview(request.session_id, session)

    return {
        "evaluation": evaluation,
        "next_question": next_question,
        "completed": completed,
    }

@app.post("/end")
def end_interview(request: StartRequest):
    session = get_session(request.session_id)

    if not session["started"]:
        raise HTTPException(
            status_code=409,
            detail="Start the interview before ending it.",
        )

    session["ended"] = True

    # Save the interview if local JSON persistence is configured.
    if session["results"]:
        save_interview(request.session_id, session)

    return {
        "status": "ended",
        "questions_attempted": len(session["results"]),
    }

@app.get("/report/{session_id}")
def get_report(session_id: str):
    session = get_session(session_id)

    if not session["started"]:
        raise HTTPException(
            status_code=409,
            detail="Interview has not started.",
        )

    if (
        session["current_index"] < len(session["questions"])
        and not session.get("ended", False)
    ):
        raise HTTPException(
            status_code=409,
            detail="End the interview before viewing an early report.",
        )

    results = session["results"]

    if not results:
        raise HTTPException(
            status_code=422,
            detail="No answers have been evaluated.",
        )

    total_points = sum(
        result["evaluation"]["total_score"]
        for result in results
    )

    maximum_points = len(results) * 10

    return {
        "role": session["role"],
        "questions_attempted": len(results),
        "total_points": total_points,
        "maximum_points": maximum_points,
        "overall_percentage": round(
                total_points / maximum_points * 100, 2
            ) if maximum_points else 0,
        "results": results,
    }

@app.get("/history")
def interview_history():
    return {"interviews": get_history()}


@app.get("/history/{session_id}")
def saved_interview_report(session_id: str):
    report = get_saved_report(session_id)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Saved interview report not found.",
        )

    return report