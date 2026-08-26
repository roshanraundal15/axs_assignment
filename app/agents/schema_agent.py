"""Schema Agent: identify relevant tables and columns for a natural language question."""
from app.agents.llm import call_llm, extract_json
from app.db.schema_info import SCHEMA_DESCRIPTION, TABLE_LIST


def run_schema_agent(question: str) -> dict:
    system = (
        "You are a database schema expert. Given a user question and a schema, "
        "return ONLY valid JSON with keys: relevant_tables (list of table names), "
        "relevant_columns (dict of table -> list of columns), reasoning (short string). "
        "Pick only tables needed to answer the question."
    )
    user = f"Schema:\n{SCHEMA_DESCRIPTION}\n\nQuestion: {question}"
    raw = call_llm(system, user)

    if raw.startswith("[NO_LLM]") or raw.startswith("[LLM_ERROR]"):
        return _heuristic_schema(question)

    data = extract_json(raw)
    if not data or "relevant_tables" not in data:
        return _heuristic_schema(question)

    # Sanitize
    tables = [t for t in data.get("relevant_tables", []) if t in TABLE_LIST]
    if not tables:
        tables = _heuristic_schema(question)["relevant_tables"]
    return {
        "relevant_tables": tables,
        "relevant_columns": data.get("relevant_columns", {}),
        "reasoning": data.get("reasoning", ""),
        "raw": raw,
    }


def _heuristic_schema(question: str) -> dict:
    q = question.lower()
    tables = set()
    if any(w in q for w in ["customer", "client", "signup", "city"]):
        tables.add("customers")
    if any(w in q for w in ["employee", "salary", "department", "hire", "manager"]):
        tables.add("employees")
    if any(w in q for w in ["project", "budget", "lead"]):
        tables.add("projects")
    if any(w in q for w in ["sale", "sales", "revenue", "amount", "product", "region", "total", "sum", "average", "count"]):
        tables.add("sales")
    if not tables:
        tables = {"sales", "customers"}
    # Joins often need customers with sales
    if "sales" in tables and ("customer" in q or "who" in q):
        tables.add("customers")
    if "project" in tables and "customer" in q:
        tables.add("customers")
    return {
        "relevant_tables": list(tables),
        "relevant_columns": {},
        "reasoning": "Heuristic keyword match (no LLM key configured)",
        "raw": "",
    }
