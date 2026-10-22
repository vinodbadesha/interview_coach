
import json

from analyze import analyze_resume
from questions_gen import build_session
from evaluator import score_answer


def run_interview(role, resume_path):
    print("\n=== AI INTERVIEW PRACTICE ===")
    print(f"Target role: {role}")

    # Step 1: Analyze the resume
    print("\nAnalyzing your resume...")

    resume_data = analyze_resume(resume_path)

    print("Resume analysis completed.")

    # Step 2: Generate questions
    print("\nPreparing your interview questions...")

    questions = build_session(
        role,
        resume_data,
        n_bank=5,
        n_resume=3,
    )

    if not questions:
        raise ValueError("No interview questions were generated.")

    print(f"Prepared {len(questions)} questions.")

    # Step 3: Wait for the candidate to start
    input("\nPress ENTER when you are ready to start...")

    results = []

    # Step 4: Ask and evaluate each question
    for index, question in enumerate(questions, start=1):
        print("\n" + "=" * 55)
        print(f"Question {index} of {len(questions)}")
        print(f"Category: {question.get('category', 'General')}")
        print("=" * 55)

        print("\n" + question["question"])

        answer = input("\nYour answer (type 'quit' to stop): ").strip()

        if answer.lower() == "quit":
            print("\nInterview stopped by candidate.")
            break

        if not answer:
            print("Empty answer. Please answer the question.")
            continue

        print("\nEvaluating your answer...")

        try:
            evaluation = score_answer(
                question,
                answer,
                role,
            )

        except Exception as error:
            print(f"Evaluation failed: {error}")
            print("This question will not be included in the score.")
            continue

        results.append({
            "question_number": index,
            "category": question.get("category", "General"),
            "question": question["question"],
            "answer": answer,
            "evaluation": evaluation,
        })

        print(
            f"\nScore: {evaluation['total_score']}/10"
        )
        print("Feedback:", evaluation["feedback"])

        print("\nAreas to improve:")
        for suggestion in evaluation["improvements"]:
            print(f"- {suggestion}")

        input("\nPress ENTER for the next question...")

    # Step 5: Calculate the final report
    print("\n" + "=" * 55)
    print("INTERVIEW SUMMARY")
    print("=" * 55)

    if not results:
        print("No answers were evaluated. No final score available.")
        return

    total_score = sum(
        item["evaluation"]["total_score"]
        for item in results
    )

    max_score = len(results) * 10
    percentage = (total_score / max_score) * 100

    print(f"Role: {role}")
    print(f"Questions evaluated: {len(results)}")
    print(f"Total points: {total_score:.1f}/{max_score}")
    print(f"Overall score: {percentage:.1f}%")

    print("\nQUESTION-BY-QUESTION BREAKDOWN")

    for item in results:
        evaluation = item["evaluation"]

        print(
            f"\nQ{item['question_number']}: "
            f"{evaluation['total_score']}/10"
        )
        print(item["question"])
        print("Feedback:", evaluation["feedback"])

    # Step 6: Save the report
    report = {
        "role": role,
        "questions_attempted": len(results),
        "total_points": total_score,
        "maximum_points": max_score,
        "overall_percentage": round(percentage, 2),
        "results": results,
    }

    with open("interview_report.json", "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\nReport saved to interview_report.json")


if __name__ == "__main__":
    target_role = input(
        "Enter the role you want to practise for "
        "(e.g. GenAI Intern): "
    ).strip()

    resume_path = input(
        "Enter your resume file path (e.g. resume.pdf): "
    ).strip()

    if not target_role or not resume_path:
        print("Role and resume path are required.")
    else:
        run_interview(target_role, resume_path)
