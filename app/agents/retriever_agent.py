"""Retriever Agent: execute SQL safely and return rows."""
import os
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/axs_rag"
)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def run_retriever_agent(sql: str) -> dict:
    sql_clean = sql.strip().rstrip(";")
    # Safety: only SELECT
    if not sql_clean.lower().startswith("select") or ";" in sql_clean:
        return {
            "success": False,
            "error": "Only one SELECT query is allowed.",
            "rows": [],
            "columns": [],
        }
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(sql_clean))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchmany(200)]
            # Serialize non-JSON types
            for r in rows:
                for k, v in list(r.items()):
                    if hasattr(v, "isoformat"):
                        r[k] = v.isoformat()
                    elif isinstance(v, (bytes,)):
                        r[k] = str(v)
                    else:
                        try:
                            float(v)  # Decimal ok via float
                            r[k] = float(v) if not isinstance(v, (int, float, str, type(None), bool)) else v
                        except Exception:
                            r[k] = str(v)
        return {
            "success": True,
            "error": None,
            "rows": rows,
            "columns": columns,
            "row_count": len(rows),
        }
    except SQLAlchemyError as e:
        return {
            "success": False,
            "error": str(e.orig) if hasattr(e, "orig") else str(e),
            "rows": [],
            "columns": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "rows": [],
            "columns": [],
        }
