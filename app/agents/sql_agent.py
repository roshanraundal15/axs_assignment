"""SQL Generator Agent: produce a safe PostgreSQL SELECT query."""
import re
from app.agents.llm import call_llm, extract_json
from app.db.schema_info import SCHEMA_DESCRIPTION


FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def run_sql_agent(question: str, schema_context: dict) -> dict:
    tables = schema_context.get("relevant_tables", [])
    system = (
        "You are an expert PostgreSQL query writer. "
        "Return ONLY valid JSON: {\"sql\": \"SELECT ...\", \"explanation\": \"...\"}. "
        "Rules: ONLY SELECT queries. Use proper JOINs. "
        "For temporal phrases: last year, this year, Q1 2024, etc., use PostgreSQL date logic. "
        "Limit results to 100 rows unless aggregation. Never modify data."
    )
    user = (
        f"Schema:\n{SCHEMA_DESCRIPTION}\n\n"
        f"Relevant tables hint: {tables}\n\n"
        f"Question: {question}\n\n"
        "Write a single PostgreSQL SELECT query that answers the question."
    )
    raw = call_llm(system, user)

    if raw.startswith("[NO_LLM]") or raw.startswith("[LLM_ERROR]"):
        return _heuristic_sql(question, tables)

    data = extract_json(raw)
    sql = (data or {}).get("sql", "").strip().rstrip(";")
    if not sql or ";" in sql or FORBIDDEN.search(sql) or not sql.lower().startswith("select"):
        return _heuristic_sql(question, tables)

    return {
        "sql": sql,
        "explanation": (data or {}).get("explanation", ""),
        "raw": raw,
    }


def _heuristic_sql(question: str, tables: list) -> dict:
    """Simple rule-based SQL for demo without LLM key."""
    q = question.lower()

    if "count" in q and "customer" in q:
        return {"sql": "SELECT COUNT(*) AS customer_count FROM customers", "explanation": "Count customers", "raw": ""}
    if "count" in q and "employee" in q:
        return {"sql": "SELECT COUNT(*) AS employee_count FROM employees", "explanation": "Count employees", "raw": ""}
    if "count" in q and "active" in q and "customer" in q:
        return {"sql": "SELECT COUNT(*) AS active_customer_count FROM customers WHERE status = 'active'", "explanation": "Count active customers", "raw": ""}
    if any(word in q for word in ["list", "show", "find"]):
        if "active" in q and "customer" in q:
            return {"sql": "SELECT customer_id, name, city, signup_date FROM customers WHERE status = 'active' LIMIT 50", "explanation": "List active customers", "raw": ""}
        department = next((name for name in ["engineering", "sales", "support", "finance", "operations"] if name in q), None)
        if department and "employee" in q:
            return {"sql": f"SELECT employee_id, name, role, hire_date FROM employees WHERE department = '{department.title()}' LIMIT 50", "explanation": f"List {department.title()} employees", "raw": ""}
    if "average" in q and "salary" in q:
        return {
            "sql": "SELECT department, ROUND(AVG(salary)::numeric, 2) AS avg_salary FROM employees GROUP BY department ORDER BY avg_salary DESC",
            "explanation": "Average salary by department",
            "raw": "",
        }
    if "total" in q and ("sale" in q or "revenue" in q):
        if "region" in q:
            return {
                "sql": "SELECT region, ROUND(SUM(amount)::numeric, 2) AS total_sales FROM sales GROUP BY region ORDER BY total_sales DESC",
                "explanation": "Total sales by region",
                "raw": "",
            }
        return {
            "sql": "SELECT ROUND(SUM(amount)::numeric, 2) AS total_sales FROM sales",
            "explanation": "Total sales amount",
            "raw": "",
        }
    if ("sales" in q or "revenue" in q) and "product" in q:
        return {"sql": "SELECT product, ROUND(SUM(amount)::numeric, 2) AS total_sales FROM sales GROUP BY product ORDER BY total_sales DESC", "explanation": "Total sales by product", "raw": ""}
    if "top" in q and "customer" in q:
        return {
            "sql": (
                "SELECT c.name, ROUND(SUM(s.amount)::numeric, 2) AS total_spent "
                "FROM sales s JOIN customers c ON s.customer_id = c.customer_id "
                "GROUP BY c.customer_id, c.name ORDER BY total_spent DESC LIMIT 10"
            ),
            "explanation": "Top customers by spend",
            "raw": "",
        }
    if "last year" in q and "sale" in q:
        return {
            "sql": (
                "SELECT ROUND(SUM(amount)::numeric, 2) AS total_sales "
                "FROM sales WHERE sale_date >= date_trunc('year', CURRENT_DATE) - INTERVAL '1 year' "
                "AND sale_date < date_trunc('year', CURRENT_DATE)"
            ),
            "explanation": "Sales last calendar year",
            "raw": "",
        }
    quarter = re.search(r"\bq([1-4])\s*(20\d{2})\b", q)
    if quarter and ("sale" in q or "revenue" in q):
        quarter_number, year = int(quarter.group(1)), int(quarter.group(2))
        start_month = (quarter_number - 1) * 3 + 1
        start = f"{year}-{start_month:02d}-01"
        next_year = year + (1 if quarter_number == 4 else 0)
        next_month = 1 if quarter_number == 4 else start_month + 3
        end = f"{next_year}-{next_month:02d}-01"
        return {"sql": f"SELECT ROUND(SUM(amount)::numeric, 2) AS total_sales FROM sales WHERE sale_date >= '{start}' AND sale_date < '{end}'", "explanation": f"Sales for Q{quarter_number} {year}", "raw": ""}
    if "active" in q and "project" in q:
        return {
            "sql": "SELECT project_id, project_name, budget, status FROM projects WHERE status = 'active' LIMIT 50",
            "explanation": "Active projects",
            "raw": "",
        }
    if "employee" in q and "engineering" in q:
        return {
            "sql": "SELECT employee_id, name, role, salary FROM employees WHERE department = 'Engineering' LIMIT 50",
            "explanation": "Engineering employees",
            "raw": "",
        }
    # Default safe query
    return {
        "sql": "SELECT sale_id, customer_id, amount, product, region, sale_date FROM sales ORDER BY sale_date DESC LIMIT 20",
        "explanation": "Recent sales (fallback)",
        "raw": "",
    }
