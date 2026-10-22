
import { useState } from "react";
import "./App.css";

const API = "";

async function apiRequest(path, options = {}) {
  let response;

  try {
    response = await fetch(`${API}${path}`, options);
  } catch {
    throw new Error(
      "Cannot connect to the backend. Start FastAPI on port 8000."
    );
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Something went wrong. Please try again."
    );
  }

  return data;
}

export default function App() {
  const [role, setRole] = useState("");
  const [resume, setResume] = useState(null);

  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [completedQuestions, setCompletedQuestions] = useState(0);

  const [answer, setAnswer] = useState("");
  const [evaluation, setEvaluation] = useState(null);
  
  const [report, setReport] = useState(null);
  const [history, setHistory] = useState([]);
  const [viewingHistory, setViewingHistory] = useState(false);

  const [stage, setStage] = useState("setup");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  async function prepareInterview(event) {
    event.preventDefault();

    if (!role.trim() || !resume) {
      setError("Enter your target role and upload your PDF resume.");
      return;
    }

    if (!resume.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF resume.");
      return;
    }

    if (resume.size > 5 * 1024 * 1024) {
      setError("Your resume must be 5 MB or smaller.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const form = new FormData();
      form.append("role", role.trim());
      form.append("resume", resume);

      const data = await apiRequest("/prepare", {
        method: "POST",
        body: form,
      });

      setSessionId(data.session_id);
      setTotalQuestions(data.total_questions);
      setCompletedQuestions(0);
      setStage("ready");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function startInterview() {
    setLoading(true);
    setError("");

    try {
      const data = await apiRequest("/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      setQuestion(data.question);
      setAnswer("");
      setEvaluation(null);
      setStage("interview");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function submitAnswer(event) {
    event.preventDefault();

    if (!answer.trim()) {
      setError("Please enter your answer.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await apiRequest("/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          answer: answer.trim(),
        }),
      });

      setEvaluation(data.evaluation);
      setQuestion(data.next_question);
      setCompletedQuestions((count) => count + 1);
      setStage(data.completed ? "last-answer" : "feedback");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function continueInterview() {
    if (!question) {
      await loadReport();
      return;
    }

    setAnswer("");
    setEvaluation(null);
    setStage("interview");
    setError("");
  }

  async function endInterview() {
  if (
    !window.confirm(
      "End this interview now and view your report?"
    )
  ) {
    return;
  }

  setLoading(true);
  setError("");

  try {
    await apiRequest("/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    });

    const data = await apiRequest(
      `/report/${encodeURIComponent(sessionId)}`
    );

    setReport(data);
    setViewingHistory(false);
    setStage("report");
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

  async function loadReport() {
    setLoading(true);
    setError("");

    try {
      const data = await apiRequest(
        `/report/${encodeURIComponent(sessionId)}`
      );

      setReport(data);
      setStage("report");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory() {
  setLoading(true);
  setError("");

  try {
    const data = await apiRequest("/history");

    setHistory(data.interviews || []);
    setViewingHistory(false);
    setStage("history");
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

async function openSavedReport(id) {
  setLoading(true);
  setError("");

  try {
    const data = await apiRequest(
      `/history/${encodeURIComponent(id)}`
    );

    setReport(data);
    setViewingHistory(true);
    setStage("report");
  } catch (err) {
    setError(err.message);
  } finally {
    setLoading(false);
  }
}

  function restart() {
    setRole("");
    setResume(null);
    setSessionId(null);
    setQuestion(null);
    setEvaluation(null);
    setReport(null);
    setAnswer("");
    setTotalQuestions(0);
    setCompletedQuestions(0);
    setError("");
    setStage("setup");
  }

  const progress =
    totalQuestions > 0
      ? (completedQuestions / totalQuestions) * 100
      : 0;

  return (
    <div className="app">
      <header className="navbar">
        <a className="logo" href="#home">
          Interview<span>Coach</span>
        </a>
        <div className="nav-actions">
          <span className="nav-label">
            AI-powered interview practice
          </span>

          <button
            type="button"
            className="nav-history-button"
            onClick={loadHistory}
            disabled={loading}
          >
            Interview History
          </button>
        </div>
      </header>

      <main className="container">
        <section className="hero" id="home">
          <p className="eyebrow">YOUR PERSONAL INTERVIEW TRAINER</p>
          <h1>
            Practice with purpose.
            <br />
            <span>Interview with confidence.</span>
          </h1>
          <p className="hero-description">
            Personalized questions from your resume, technical
            evaluations, and practical feedback to help you improve.
          </p>
        </section>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {stage === "history" && (
          <section className="panel">
            <StepHeading
              number="H"
              title="Interview History"
              subtitle="Review your previous interview attempts and performance."
            />

            {loading ? (
              <p className="body-copy">Loading interview history...</p>
            ) : history.length === 0 ? (
              <div className="history-empty">
                <h3>No completed interviews yet</h3>
                <p className="body-copy">
                  Complete your first interview and your results will appear here.
                </p>

                <button
                  className="primary"
                  onClick={restart}
                >
                  Start an interview
                </button>
              </div>
            ) : (
              <div className="history-list">
                {history.slice().reverse().map((item) => (
                  <article
                    className="history-item"
                    key={item.session_id}
                  >
                    <div className="history-item-header">
                      <div>
                        <h3>{item.role}</h3>
                        <p className="body-copy">
                          {item.questions_attempted} questions evaluated
                        </p>
                      </div>

                      <strong className="history-score">
                        {item.overall_percentage}%
                      </strong>
                    </div>

                    <div className="history-progress-track">
                      <div
                        className="history-progress-bar"
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(0, item.overall_percentage)
                          )}%`,
                        }}
                      />
                    </div>

                    <p className="body-copy">
                      Points: {item.total_points}/{item.maximum_points}
                    </p>

                    <button
                      className="secondary"
                      onClick={() => openSavedReport(item.session_id)}
                      disabled={loading}
                    >
                      View detailed report
                    </button>
                  </article>
                ))}
              </div>
            )}

            <button
              className="secondary history-back-button"
              onClick={restart}
            >
              Prepare a new interview
            </button>
          </section>
        )}

        {stage === "setup" && (
          <section className="panel">
            <StepHeading
              number="01"
              title="Set up your interview"
              subtitle="Choose the role and upload your resume."
            />

            <form onSubmit={prepareInterview}>
              <label htmlFor="role">Target role</label>
              <input
                id="role"
                value={role}
                onChange={(event) => setRole(event.target.value)}
                placeholder="e.g. GenAI Intern, Data Analyst"
                required
              />

              <label htmlFor="resume">Resume (PDF)</label>
              <input
                id="resume"
                type="file"
                accept=".pdf,application/pdf"
                onChange={(event) =>
                  setResume(event.target.files?.[0] || null)
                }
                required
              />

              <p className="hint">PDF only · Maximum size 5 MB</p>

              <button className="primary" disabled={loading}>
                {loading ? "Analyzing resume..." : "Prepare interview"}
              </button>
            </form>
          </section>
        )}

        {stage === "ready" && (
          <section className="panel">
            <StepHeading
              number="02"
              title="You're ready"
              subtitle={`${role} · ${totalQuestions} questions prepared.`}
            />

            <ul className="feature-list">
              <li>Questions tailored to your resume</li>
              <li>Role-specific technical questions</li>
              <li>Individual scores and actionable feedback</li>
            </ul>

            <button
              className="primary"
              onClick={startInterview}
              disabled={loading}
            >
              {loading ? "Starting..." : "Start interview"}
            </button>
          </section>
        )}

        {stage === "interview" && question && (
          <section className="panel">
            <div className="question-meta">
              <span>
                Question {question.question_number} of {totalQuestions}
              </span>
              <span className="category">
                {question.category || "General"}
              </span>
            </div>

            <div className="progress-track">
              <div
                className="progress-bar"
                style={{ width: `${progress}%` }}
              />
            </div>

            <h2 className="question-title">{question.question}</h2>

            <form onSubmit={submitAnswer}>
              <label htmlFor="answer">Your answer</label>
              <textarea
                id="answer"
                rows="7"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                placeholder="Explain your approach and give examples..."
                required
              />

              <p className="hint">
                Take your time. Be specific and explain your reasoning.
              </p>

              <button className="primary" disabled={loading}>
                {loading ? "Evaluating answer..." : "Submit answer"}
              </button>
            </form>
            <button
              type="button"
              className="secondary"
              onClick={endInterview}
              disabled={loading}
            >
              End interview
            </button>
          </section>
        )}

        {(stage === "feedback" || stage === "last-answer") &&
          evaluation && (
            <section className="panel">
              <div className="score-header">
                <div>
                  <p className="eyebrow">YOUR ANSWER SCORE</p>
                  <h2 className="big-score">
                    {evaluation.total_score}
                    <span>/10</span>
                  </h2>
                </div>
                <span className="completed-badge">Evaluated</span>
              </div>

              <div className="score-grid">
                {[
                  ["Relevance", "relevance", 2],
                  ["Technical correctness", "technical_correctness", 3],
                  ["Completeness", "completeness", 3],
                  ["Communication", "communication", 2],
                ].map(([label, key, max]) => (
                  <div className="score-card" key={key}>
                    <span>{label}</span>
                    <strong>
                      {evaluation.scores[key]}/{max}
                    </strong>
                  </div>
                ))}
              </div>

              <FeedbackList
                title="What went well"
                items={evaluation.strengths}
              />

              <FeedbackList
                title="Areas to improve"
                items={evaluation.improvements}
              />

              <h3>Feedback</h3>
              <p className="body-copy">{evaluation.feedback}</p>

              <h3>Example of a stronger answer</h3>
              <p className="sample-answer">
                {evaluation.improved_answer}
              </p>

              <button
                className="primary"
                onClick={continueInterview}
                disabled={loading}
              >
                {loading
                  ? "Loading report..."
                  : stage === "last-answer"
                    ? "View final report"
                    : "Next question"}
              </button>
              {stage === "feedback" && (
                <button
                  type="button"
                  className="secondary"
                  onClick={endInterview}
                  disabled={loading}
                >
                  End interview & view report
                </button>
              )}
            </section>
          )}

        {stage === "report" && report && (
          <section className="panel">
            <p className="eyebrow">INTERVIEW COMPLETE</p>
            <h2>Your performance report</h2>
            <p className="body-copy">Target role: {report.role}</p>

            <div className="report-grid">
              <div className="report-card">
                <span>Overall score</span>
                <strong>{report.overall_percentage}%</strong>
              </div>
              <div className="report-card">
                <span>Points earned</span>
                <strong>
                  {report.total_points}/{report.maximum_points}
                </strong>
              </div>
              <div className="report-card">
                <span>Questions evaluated</span>
                <strong>{report.questions_attempted}</strong>
              </div>
            </div>

            <h3>Review your answers</h3>

            {report.results.map((result) => (
              <article
                className="report-question"
                key={result.question_number}
              >
                <div className="question-meta">
                  <span>Question {result.question_number}</span>
                  <strong>
                    {result.evaluation.total_score}/10
                  </strong>
                </div>
                <h4>{result.question}</h4>
                <p className="body-copy">
                  {result.evaluation.feedback}
                </p>
                <FeedbackList
                  title="Suggestions"
                  items={result.evaluation.improvements}
                />
              </article>
            ))}

            {viewingHistory ? (
  <button
    className="secondary"
    onClick={loadHistory}
    disabled={loading}
  >
    Back to interview history
  </button>
) : (
  <button className="secondary" onClick={restart}>
    Practice another interview
  </button>
)}
          </section>
        )}

        <footer>
          Practice, learn, improve. Your next interview starts here.
        </footer>
      </main>
    </div>
  );
}

function StepHeading({ number, title, subtitle }) {
  return (
    <div className="step-heading">
      <span className="step-number">{number}</span>
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
    </div>
  );
}

function FeedbackList({ title, items }) {
  return (
    <div className="feedback-list">
      <h3>{title}</h3>
      {items?.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${index}-${item}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="body-copy">No specific items returned.</p>
      )}
    </div>
  );
}
