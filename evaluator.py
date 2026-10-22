
import json
from analyze import ask_llm, parse_json


def validate_evaluation(data):
    if not isinstance(data, dict):
        return False

    limits = {
        "relevance": 2,
        "technical_correctness": 3,
        "completeness": 3,
        "communication": 2,
    }

    scores = data.get("scores")

    if not isinstance(scores, dict):
        return False

    for criterion, maximum in limits.items():
        score = scores.get(criterion)

        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= maximum
        ):
            return False

    total = data.get("total_score")

    if (
        isinstance(total, bool)
        or not isinstance(total, (int, float))
        or abs(total - sum(scores[k] for k in limits)) > 0.01
    ):
        return False

    if not 0 <= total <= 10:
        return False

    for field in ("strengths", "improvements"):
        if not isinstance(data.get(field), list):
            return False

    for field in ("feedback", "improved_answer"):
        if not isinstance(data.get(field), str):
            return False

    return True


def score_answer(question_data, answer, role):
    if not answer or not answer.strip():
        raise ValueError("Answer cannot be empty.")

    key_points = question_data.get("key_points", [])

    if not key_points:
        raise ValueError("Question has no scoring key points.")

    prompt = f"""
You are a fair technical interview evaluator.

Candidate role: {role}

Question: {question_data["question"]}

Expected answer key points:
{json.dumps(key_points)}

Candidate answer:
{answer}

Score the answer using this rubric:
- Relevance: 0 to 2
- Technical correctness: 0 to 3
- Completeness: 0 to 3
- Communication: 0 to 2

Rules:
- Judge meaning, not exact wording.
- Give credit for correct equivalent explanations.
- Do not invent candidate experience.
- Do not reward unnecessary length.
- Explain strengths and specific areas for improvement.
- Provide a concise example of a stronger answer.
- The total must equal the sum of the four criterion scores.
- Return only valid JSON, without Markdown.

Required structure:
{{
  "scores": {{
    "relevance": 0,
    "technical_correctness": 0,
    "completeness": 0,
    "communication": 0
  }},
  "total_score": 0,
  "strengths": ["..."],
  "improvements": ["..."],
  "feedback": "...",
  "improved_answer": "..."
}}
"""

    for attempt in range(2):
        raw = ask_llm(prompt, temperature=0.1)
        result = parse_json(raw)

        if validate_evaluation(result):
            return result

        prompt += (
            "\nYour previous response was invalid. Return the exact "
            "required JSON structure with valid numeric scores."
        )

    raise ValueError("Could not obtain a valid evaluation.")


if __name__ == "__main__":
    question = {
        "question": "What is the difference between a list and a tuple in Python?",
        "category": "Python",
        "key_points": [
            "Lists are mutable.",
            "Tuples are immutable.",
            "Both can store multiple elements.",
        ],
    }

    answer = (
        "A list is mutable, so its elements can be changed. "
        "A tuple is immutable after creation. Both store multiple elements."
    )

    result = score_answer(question, answer, "GenAI Intern")
    print(json.dumps(result, indent=2))
