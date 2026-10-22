
import json
import random
from pathlib import Path

from analyze import ask_llm, parse_json


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BANK_PATH = BASE_DIR / "questions.json"


def load_bank(role, path=DEFAULT_BANK_PATH):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    role_questions = [
        q for q in data
        if q.get("role", "").strip().lower() == role.strip().lower()
        and valid_question(q)
    ]

    return role_questions


def valid_question(q):
    return (
        isinstance(q, dict)
        and isinstance(q.get("question"), str)
        and bool(q["question"].strip())
        and isinstance(q.get("key_points"), list)
        and len(q["key_points"]) >= 2
    )


def generate_resume_questions(resume_data, role, n=5):
    prompt = (
        f"You are an interviewer for a {role} position. "
        f"Generate exactly {n} distinct interview questions using the resume below. "
        "Questions must refer to specific projects, skills, or experience actually "
        "mentioned in the resume. Do not invent experience. "
        "Vary the questions between project decisions, implementation, challenges, "
        "technical concepts, and results. "
        "Each question must have at least 2 key points for evaluating the answer. "
        'Return ONLY JSON in this format: {"questions": ['
        '{"category": "Project", "question": "...", '
        '"key_points": ["...", "..."]}]}.\n\n'
        f"Resume data:\n{json.dumps(resume_data, ensure_ascii=False)}"
    )

    collected = []
    seen = set()

    for attempt in range(3):
        remaining = n - len(collected)

        if remaining <= 0:
            break

        retry_prompt = prompt

        if attempt > 0:
            retry_prompt += (
                f"\nGenerate {remaining} additional questions. "
                "Do not repeat these existing questions:\n"
                + json.dumps([q["question"] for q in collected])
            )

        try:
            data = parse_json(
                ask_llm(retry_prompt, temperature=0.7)
            )
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        questions = data.get("questions", [])

        if not isinstance(questions, list):
            continue

        for q in questions:
            if not valid_question(q):
                continue

            text = q["question"].strip()
            normalized = text.lower()

            if normalized in seen:
                continue

            seen.add(normalized)
            collected.append({
                "id": f"resume-{len(collected) + 1:03d}",
                "source": "resume",
                "role": role,
                "category": q.get("category", "Resume"),
                "question": text,
                "key_points": q["key_points"],
            })

            if len(collected) >= n:
                break

    return collected[:n]


def generate_role_questions(role, n=10):
    prompt = (
        f"Create exactly {n} interview questions for an entry-level "
        f"{role} candidate. Cover different relevant technical concepts, "
        "practical scenarios, troubleshooting, and problem-solving. "
        "Avoid repeated or nearly identical questions. "
        "Each question needs at least 2 evaluation key points. "
        'Return ONLY valid JSON: {"questions": ['
        '{"category": "Technical", "question": "...", '
        '"key_points": ["...", "..."]}]}'
    )

    collected = []
    seen = set()

    for attempt in range(3):
        remaining = n - len(collected)

        if remaining <= 0:
            break

        retry_prompt = prompt

        if attempt > 0:
            retry_prompt += (
                f"\nGenerate {remaining} additional distinct questions. "
                "Do not repeat these:\n"
                + json.dumps([q["question"] for q in collected])
            )

        try:
            data = parse_json(
                ask_llm(retry_prompt, temperature=0.7)
            )
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        questions = data.get("questions", [])

        if not isinstance(questions, list):
            continue

        for q in questions:
            if not valid_question(q):
                continue

            text = q["question"].strip()
            normalized = text.lower()

            if normalized in seen:
                continue

            seen.add(normalized)
            collected.append({
                "id": f"generated-{len(collected) + 1:03d}",
                "source": "generated",
                "role": role,
                "category": q.get("category", "Technical"),
                "question": text,
                "key_points": q["key_points"],
            })

            if len(collected) >= n:
                break

    return collected[:n]


def build_session(role, resume_data, n_bank=10, n_resume=5):
    bank = load_bank(role)
    random.shuffle(bank)

    picked = []
    seen_categories = set()
    seen_questions = set()

    # Select different categories first.
    for q in bank:
        normalized = q["question"].strip().lower()

        if (
            q["category"] not in seen_categories
            and normalized not in seen_questions
        ):
            picked.append(q)
            seen_categories.add(q["category"])
            seen_questions.add(normalized)

    # Fill remaining slots from the question bank.
    for q in bank:
        if len(picked) >= n_bank:
            break

        normalized = q["question"].strip().lower()

        if normalized not in seen_questions:
            picked.append(q)
            seen_questions.add(normalized)

    # Generate additional role-specific questions if the bank is too small.
    if len(picked) < n_bank:
        generated = generate_role_questions(
            role,
            n=n_bank - len(picked),
        )

        for q in generated:
            normalized = q["question"].strip().lower()

            if normalized not in seen_questions:
                picked.append(q)
                seen_questions.add(normalized)

    # Generate resume-specific questions.
    resume_questions = generate_resume_questions(
        resume_data,
        role,
        n=n_resume,
    )

    for q in resume_questions:
        normalized = q["question"].strip().lower()

        if normalized not in seen_questions:
            picked.append(q)
            seen_questions.add(normalized)

    return picked


if __name__ == "__main__":
    from analyze import analyze_resume

    resume_data = analyze_resume("resume.pdf")
    questions = build_session(
        "GenAI Intern",
        resume_data,
        n_bank=10,
        n_resume=5,
    )

    print(f"\nPrepared {len(questions)} questions.\n")

    for i, question in enumerate(questions, 1):
        print(
            f"{i}. [{question['source']}] "
            f"{question['category']}: {question['question']}"
        )
