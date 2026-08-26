# Multi-Agent RAG Analytics

Natural-language analytics for a relational PostgreSQL database. Ask a business question in plain English and the application selects relevant schema, generates a read-only SQL query, retrieves data, and produces a human-readable answer.

The project also includes an optional document-retrieval fallback. When the database path cannot answer a question, the system searches internal notes using lightweight TF-IDF retrieval and returns an answer based on the matching context.

## What It Includes

- FastAPI web application with `POST /ask` and `GET /health`
- Four modular agents: Schema, SQL Generator, Retriever, and Synthesizer
- PostgreSQL database with four related tables
- Deterministic synthetic data generator
- LLM support through Groq or an OpenAI-compatible provider
- Heuristic fallbacks for common questions when no LLM key is configured
- Read-only SQL enforcement, including multi-statement rejection
- Document and PDF fallback retrieval using TF-IDF
- Dark analyst-console web interface
- Focused automated tests for safety and core query behavior

## Architecture

```text
User question
     |
     v
Schema Agent       -> identifies relevant tables
     |
     v
SQL Generator      -> creates a PostgreSQL SELECT query
     |
     v
Retriever Agent    -> executes the query and returns rows
     |
     v
Synthesizer Agent  -> writes the final answer
     |
     v
JSON response + web interface

If the SQL path fails or returns no rows:
     |
     v
Document fallback -> TF-IDF search over data/docs/
```

## Agent Responsibilities

| Agent | Responsibility |
| --- | --- |
| Schema Agent | Maps the question to relevant tables and columns using the LLM or keyword heuristics. |
| SQL Generator Agent | Produces a PostgreSQL `SELECT` query with joins, filters, aggregations, and date logic. |
| Retriever Agent | Executes one read-only query through SQLAlchemy and returns up to 200 rows. |
| Synthesizer Agent | Converts retrieved rows into a concise natural-language answer. |
| Vector Fallback Agent | Searches `.txt`, `.md`, and `.pdf` files when the SQL path cannot answer. |

## How It Works

When a user submits a question in the web interface, the browser sends the text to `POST /ask`. The complete workflow runs synchronously on the FastAPI server and returns one JSON response.

### 1. Request validation

`app/main.py` validates the request with Pydantic before the pipeline starts. The `question` field is required and must contain between 3 and 1,000 characters. Invalid requests receive an HTTP 422 response.

### 2. Schema selection

The Schema Agent receives the question together with the schema description from `app/db/schema_info.py`. It identifies the tables and fields likely to be relevant, for example `sales` and `customers` for a question about customer spending.

When an LLM is configured, it returns structured JSON containing relevant tables, columns, and reasoning. If the LLM is unavailable or returns invalid data, the agent uses keyword heuristics so common questions can still be processed.

### 3. SQL generation

The SQL Generator Agent receives the question, schema description, and selected tables. It creates a PostgreSQL query using joins, filters, grouping, aggregation, and date conditions when required.

Before execution, the query is checked to ensure that it begins with `SELECT`, contains no data-changing keywords such as `INSERT`, `UPDATE`, or `DROP`, and contains no multiple SQL statements. Normal lookups are also limited to a safe result size.

If no LLM is configured, the heuristic generator handles common examples such as counts, active customers, sales by region or product, top customers, last-year sales, and quarter-based sales queries.

### 4. Database retrieval

The Retriever Agent connects to PostgreSQL using `DATABASE_URL` and executes the validated query through SQLAlchemy. It returns column names, rows, a row count, and any database error. The retriever fetches at most 200 rows, while the final API response exposes at most 15 sample rows. Dates and numeric values are converted to JSON-compatible values.

### 5. Answer synthesis

If rows are returned, the Synthesizer Agent receives the question, generated SQL, and retrieved data. It produces a concise answer using only those results. With an LLM it generates a natural-language summary; without one, it creates a deterministic summary from the returned rows.

### 6. Document fallback

If schema selection fails, SQL generation fails, the database query fails, or the query returns no rows, the orchestrator tries document fallback. The Vector Fallback Agent loads files from `data/docs/`, splits them into overlapping chunks, scores them with TF-IDF similarity, and selects the most relevant context. The configured LLM then answers using only that context. Without an LLM, an extractive answer includes matching document names and text previews.

Successful fallback responses are marked with `steps.source: "document_rag"`; database responses use `steps.source: "sql"`.

### 7. Response and interface rendering

The response includes the original question, answer, intermediate steps, and an error code when applicable. The frontend displays the answer source, relevant tables, generated SQL, query explanation, sample rows, and document sources when fallback RAG is used. Database values are rendered as text, and recent queries are stored locally in the browser rather than on the server.

### Example flow

For `What were total sales by region?`, the normal path is:

```text
Question
  -> Schema Agent selects sales
  -> SQL Agent creates SUM(amount) GROUP BY region
  -> Retriever executes the SELECT query
  -> Synthesizer explains the regional totals
  -> API returns answer, SQL, columns, and sample rows
```

For a company-policy question that is not represented in the database, the document fallback searches the notes in `data/docs/` and returns the best available answer.

## Database

The database is PostgreSQL, using the name `axs_rag` by default. The schema contains four interrelated tables:

- `customers`: approximately 200 records
- `employees`: 100 records
- `projects`: approximately 120 records
- `sales`: approximately 800 records

Every table meets the assignment target of 100 to 1,000 synthetic rows after seeding. Relationships are defined through customer, employee, project, and manager foreign keys.

## Prerequisites

- Python 3.10 or newer
- PostgreSQL 14 or newer
- PostgreSQL command-line tools (`psql`) available in your terminal
- An optional Groq or OpenAI API key for LLM-generated queries and answers

## Windows Setup

### 1. Open the project

In VS Code, open a terminal and run:

```cmd
cd /d C:\Users\Roshan\axs-multi-agent-rag
```

### 2. Confirm PostgreSQL is installed

```cmd
psql --version
```

If the command is not recognized, add the PostgreSQL `bin` directory to your Windows `PATH`. It is commonly located at:

```text
C:\Program Files\PostgreSQL\14\bin
```

Replace `14` with your installed version.

### 3. Start PostgreSQL

Open **Command Prompt as Administrator** and run the service name installed on your computer:

```cmd
net start postgresql-x64-14
```

To find the exact service name:

```cmd
sc query type= service state= all | findstr /I postgres
```

If PostgreSQL is already running, you can skip this step.

### 4. Create the database

Connect to PostgreSQL:

```cmd
psql -U postgres
```

At the `postgres=#` prompt, create the database and exit:

```sql
CREATE DATABASE axs_rag;
\q
```

If you see `database "axs_rag" already exists`, that is fine. Exit with `\q` and continue.

Do not run Windows commands such as `psql ... -f ...` at the `postgres=#` prompt. Run them after returning to the normal `C:\...>` terminal prompt.

### 5. Create the tables

From the project root:

```cmd
psql -U postgres -d axs_rag -f scripts\init_db.sql
```

This creates the tables and indexes. The script drops and recreates these project tables, so do not run it against a database containing data you need to preserve.

### 6. Create and activate a virtual environment

```cmd
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

When activated, your prompt normally begins with `(venv)`.

### 7. Configure environment variables

Copy `.env.example` to `.env` and edit the database password:

```cmd
copy .env.example .env
```

Minimum local configuration:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/axs_rag
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

The application can answer common demo questions without an LLM key using heuristic logic. For broader natural-language questions, configure `GROQ_API_KEY` or the supported OpenAI settings. Never commit `.env` or API keys.

### 8. Seed synthetic data

```cmd
python scripts\seed_data.py
```

The script clears the four project tables and inserts fresh synthetic records. Verify the result:

```cmd
psql -U postgres -d axs_rag
```

```sql
\dt
SELECT COUNT(*) FROM customers;
SELECT COUNT(*) FROM employees;
SELECT COUNT(*) FROM projects;
SELECT COUNT(*) FROM sales;
\q
```

## Run the Application

With the virtual environment active:

```cmd
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the interface in Chrome:

```text
http://localhost:8000
```

FastAPI's interactive API documentation is available at:

```text
http://localhost:8000/docs
```

## API

### Health check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Ask a question

```http
POST /ask
Content-Type: application/json
```

Request:

```json
{
  "question": "What were total sales by region?"
}
```

Example Windows command:

```cmd
curl -X POST http://localhost:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What were total sales by region?\"}"
```

Response shape:

```json
{
  "question": "What were total sales by region?",
  "answer": "Sales by region are ...",
  "steps": {
    "relevant_schema": ["sales"],
    "generated_sql": "SELECT region, SUM(amount) ...",
    "sql_explanation": "Total sales by region",
    "result_row_count": 5,
    "result_columns": ["region", "total_sales"],
    "sample_rows": [
      {"region": "West", "total_sales": 125000}
    ],
    "source": "sql"
  },
  "error": null
}
```

The `steps.source` value is either `sql` or `document_rag`. Document fallback responses may also include `document_sources` and `document_chunks`.

## Example Questions

- How many customers do we have?
- How many active customers do we have?
- List active customers
- List employees in Engineering
- Show active projects
- What is the average salary by department?
- What were total sales by region?
- What were sales in Q1 2024?
- What were total sales last year?
- What are the top 10 customers by spend?
- Show total sales by product

The LLM path supports broader questions involving direct lookups, filters, joins, aggregations, and temporal expressions. Without an LLM key, the built-in heuristics cover the common examples above.

## Error Handling

| Situation | API behavior |
| --- | --- |
| Invalid question length | FastAPI returns HTTP 422. Questions must contain 3 to 1,000 characters. |
| No relevant schema | Attempts document fallback and reports `schema_not_found` if no source matches. |
| SQL generation failure | Attempts document fallback and reports `sql_generation_failed` if no source matches. |
| Database/query failure | Attempts document fallback and reports `retrieval_failed` if no source matches. |
| Empty database result | Attempts document fallback and reports `no_matching_records` if no source matches. |
| Unsafe or multi-statement SQL | The SQL generator falls back and the retriever rejects the query. |
| Unexpected server exception | Returns HTTP 500 with `error: server_error`. |

Database exception details are kept in intermediate agent diagnostics for troubleshooting; do not expose sensitive database configuration in a public deployment.

## Document Fallback RAG

The optional fallback reads supported files from `data/docs/`:

1. Loads `.txt`, `.md`, and `.pdf` files.
2. Splits content into overlapping chunks.
3. Builds a lightweight TF-IDF index with scikit-learn.
4. Retrieves the most relevant chunks for the question.
5. Uses the configured LLM to synthesize an answer from those chunks.

If no LLM is available, the fallback returns an extractive answer from the matching documents. Add internal notes or PDFs to `data/docs/` and restart the application to rebuild the index.

## Testing

Install the project dependencies, including `pytest`, then run:

```cmd
python -m pytest -q tests
```

The focused tests cover multi-statement SQL rejection, quarter query generation, filtered lookups, empty-result error classification, and document fallback behavior.

If your environment does not expose the same Python interpreter used by VS Code, run the command with the full path to that interpreter.

## Project Structure

```text
multi-agent-rag/
├── app/
│   ├── main.py                  # FastAPI routes and request validation
│   ├── agents/
│   │   ├── orchestrator.py     # Agent workflow and fallback routing
│   │   ├── schema_agent.py     # Table/column selection
│   │   ├── sql_agent.py        # Safe SQL generation and heuristics
│   │   ├── retriever_agent.py  # PostgreSQL execution
│   │   ├── synthesizer_agent.py# Natural-language answer generation
│   │   ├── vector_fallback_agent.py
│   │   └── llm.py              # Groq/OpenAI-compatible client
│   ├── db/schema_info.py       # Database schema supplied to the agents
│   └── templates/index.html    # Web interface
├── data/docs/                  # Internal notes used by fallback RAG
├── scripts/init_db.sql         # Tables and indexes
├── scripts/seed_data.py        # Synthetic data generation
├── tests/test_assignment.py    # Focused tests
├── requirements.txt
├── .env.example
└── README.md
```

## Security and Deployment Notes

- The retriever is intentionally read-only and rejects non-`SELECT` or multi-statement SQL.
- Use a database user with only the permissions required by the application.
- Keep `.env` out of version control.
- The bundled server is intended for local development and demonstration. Add authentication, production logging, HTTPS, and a production ASGI process before public deployment.
- The current frontend calls `/ask` on the same origin. If the frontend is hosted separately, configure FastAPI CORS and update the frontend request configuration accordingly.

## License

This repository is a demonstration project created for an AI engineering internship assignment.