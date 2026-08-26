"""Multi-agent orchestrator: Schema -> SQL -> Retriever -> Synthesizer
Falls back to document/vector RAG when SQL fails or returns no rows.
"""
from app.agents.schema_agent import run_schema_agent
from app.agents.sql_agent import run_sql_agent
from app.agents.retriever_agent import run_retriever_agent
from app.agents.synthesizer_agent import run_synthesizer_agent
from app.agents.vector_fallback_agent import run_vector_fallback_agent


def run_pipeline(question: str) -> dict:
    steps = {}
    failure_code = None

    # 1. Schema Agent
    schema_result = run_schema_agent(question)
    steps["schema_agent"] = {
        "relevant_tables": schema_result.get("relevant_tables"),
        "reasoning": schema_result.get("reasoning"),
    }

    sql_path_failed = False
    retrieval = {"success": False, "rows": [], "row_count": 0}

    if not schema_result.get("relevant_tables"):
        sql_path_failed = True
        failure_code = "schema_not_found"
    else:
        # 2. SQL Generator Agent
        sql_result = run_sql_agent(question, schema_result)
        steps["sql_generator_agent"] = {
            "sql": sql_result.get("sql"),
            "explanation": sql_result.get("explanation"),
        }

        if not sql_result.get("sql"):
            sql_path_failed = True
            failure_code = "sql_generation_failed"
        else:
            # 3. Retriever Agent
            retrieval = run_retriever_agent(sql_result["sql"])
            steps["retriever_agent"] = {
                "success": retrieval.get("success"),
                "row_count": retrieval.get("row_count", 0),
                "columns": retrieval.get("columns"),
                "error": retrieval.get("error"),
                "sample_rows": retrieval.get("rows", [])[:10],
            }

            if not retrieval.get("success"):
                sql_path_failed = True
                failure_code = "retrieval_failed"
            elif retrieval.get("row_count", 0) == 0:
                sql_path_failed = True  # empty result -> try docs
                failure_code = "no_matching_records"
            else:
                # 4. Synthesizer Agent (SQL path success)
                synthesis = run_synthesizer_agent(
                    question, sql_result["sql"], retrieval
                )
                steps["synthesizer_agent"] = {
                    "answer_preview": synthesis.get("answer", "")[:200]
                }
                return {
                    "question": question,
                    "answer": synthesis.get("answer"),
                    "steps": {
                        "relevant_schema": schema_result.get("relevant_tables"),
                        "generated_sql": sql_result.get("sql"),
                        "sql_explanation": sql_result.get("explanation"),
                        "result_row_count": retrieval.get("row_count"),
                        "result_columns": retrieval.get("columns"),
                        "sample_rows": retrieval.get("rows", [])[:15],
                        "source": "sql",
                    },
                    "error": None,
                }

    # 5. Vector / Document fallback
    fallback = run_vector_fallback_agent(question)
    steps["vector_fallback_agent"] = {
        "success": fallback.get("success"),
        "sources": fallback.get("sources"),
        "chunks": fallback.get("chunks"),
    }

    if fallback.get("success"):
        return {
            "question": question,
            "answer": fallback.get("answer"),
            "steps": {
                "relevant_schema": schema_result.get("relevant_tables"),
                "generated_sql": steps.get("sql_generator_agent", {}).get("sql"),
                "sql_explanation": "SQL path empty or failed — used document RAG fallback",
                "result_row_count": 0,
                "result_columns": [],
                "sample_rows": [],
                "document_sources": fallback.get("sources"),
                "document_chunks": fallback.get("chunks"),
                "source": "document_rag",
            },
            "error": None,
        }

    return {
        "question": question,
        "answer": fallback.get(
            "answer",
            "I could not answer from the database or documents. Please rephrase.",
        ),
        "steps": steps,
        "error": failure_code or "all_paths_failed",
    }
