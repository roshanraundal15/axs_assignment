"""
AXS Multi-Agent RAG System
POST /ask — natural language -> SQL agents -> answer
"""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.agents.orchestrator import run_pipeline

load_dotenv()

app = FastAPI(
    title="AXS Multi-Agent RAG",
    description="Natural language querying of PostgreSQL via multi-agent RAG workflow",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, examples=["What were total sales last year?"])


class AskResponse(BaseModel):
    question: str
    answer: str
    steps: dict
    error: str | None = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    try:
        result = run_pipeline(body.question.strip())
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "question": body.question,
                "answer": f"Unexpected server error: {e}",
                "steps": {},
                "error": "server_error",
            },
        )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
