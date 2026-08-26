"""Synthesizer Agent: turn SQL result rows into a natural language answer."""
import json
from app.agents.llm import call_llm


def run_synthesizer_agent(question: str, sql: str, retrieval: dict) -> dict:
    if not retrieval.get("success"):
        return {
            "answer": f"I could not retrieve data. Error: {retrieval.get('error', 'unknown')}",
            "raw": "",
        }

    rows = retrieval.get("rows", [])
    if not rows:
        return {
            "answer": "No matching records were found for your question.",
            "raw": "",
        }

    # Keep payload small for LLM
    sample = rows[:30]
    system = (
        "You are a helpful data analyst. Given a user question, the SQL used, and result rows, "
        "write a clear, concise natural language answer in 2-5 sentences. "
        "Use numbers from the data. Do not invent values."
    )
    user = (
        f"Question: {question}\n\nSQL:\n{sql}\n\n"
        f"Result rows ({len(rows)} total, showing up to 30):\n{json.dumps(sample, default=str)}"
    )
    raw = call_llm(system, user, temperature=0.2)

    if raw.startswith("[NO_LLM]") or raw.startswith("[LLM_ERROR]"):
        return {"answer": _heuristic_answer(question, rows, retrieval), "raw": raw}

    return {"answer": raw, "raw": raw}


def _heuristic_answer(question: str, rows: list, retrieval: dict) -> str:
    n = retrieval.get("row_count", len(rows))
    if n == 1 and len(rows[0]) <= 3:
        parts = [f"{k}: {v}" for k, v in rows[0].items()]
        return "Result — " + ", ".join(parts) + "."
    if n == 1:
        return f"Found 1 record: {rows[0]}."
    # Summarize first few keys
    keys = list(rows[0].keys())[:4]
    preview = "; ".join(
        ", ".join(f"{k}={r.get(k)}" for k in keys) for r in rows[:5]
    )
    return f"Found {n} records. Preview: {preview}."
