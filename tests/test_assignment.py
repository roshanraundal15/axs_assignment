from app.agents import orchestrator
from app.agents.retriever_agent import run_retriever_agent
from app.agents.sql_agent import _heuristic_sql


def test_retriever_rejects_multiple_statements():
    result = run_retriever_agent("SELECT 1; DROP TABLE customers")
    assert result["success"] is False
    assert "one SELECT" in result["error"]


def test_heuristic_supports_quarter_sales():
    result = _heuristic_sql("What were sales in Q1 2024?", ["sales"])
    assert "sale_date >= '2024-01-01'" in result["sql"]
    assert "sale_date < '2024-04-01'" in result["sql"]


def test_heuristic_supports_filtered_lookup():
    result = _heuristic_sql("List active customers", ["customers"])
    assert result["sql"] == (
        "SELECT customer_id, name, city, signup_date "
        "FROM customers WHERE status = 'active' LIMIT 50"
    )


def test_pipeline_reports_empty_result_code(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "run_schema_agent",
        lambda question: {"relevant_tables": ["sales"], "reasoning": "test"},
    )
    monkeypatch.setattr(
        orchestrator,
        "run_sql_agent",
        lambda question, schema: {"sql": "SELECT 1", "explanation": "test"},
    )
    monkeypatch.setattr(
        orchestrator,
        "run_retriever_agent",
        lambda sql: {"success": True, "rows": [], "columns": [], "row_count": 0},
    )
    monkeypatch.setattr(
        orchestrator,
        "run_vector_fallback_agent",
        lambda question: {"success": False, "answer": "No matching records."},
    )

    result = orchestrator.run_pipeline("test question")

    assert result["error"] == "no_matching_records"


def test_pipeline_uses_document_fallback(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "run_schema_agent",
        lambda question: {"relevant_tables": [], "reasoning": "test"},
    )
    monkeypatch.setattr(
        orchestrator,
        "run_vector_fallback_agent",
        lambda question: {
            "success": True,
            "answer": "Document answer",
            "sources": ["notes.txt"],
            "chunks": [],
        },
    )

    result = orchestrator.run_pipeline("company policy")

    assert result["answer"] == "Document answer"
    assert result["steps"]["source"] == "document_rag"
    assert result["error"] is None
