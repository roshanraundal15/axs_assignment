"""
Vector / Document fallback agent.

If SQL retrieval fails or returns no rows, retrieve relevant chunks from
local documents (txt/md/pdf) using TF-IDF similarity and synthesize an answer.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Dict, Any

from app.agents.llm import call_llm

DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "docs"


def _load_documents() -> List[Dict[str, str]]:
    """Load .txt, .md, and .pdf files from data/docs."""
    docs = []
    if not DOCS_DIR.exists():
        return docs

    for path in sorted(DOCS_DIR.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix in {".txt", ".md"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
            elif suffix == ".pdf":
                text = _read_pdf(path)
            else:
                continue
            text = text.strip()
            if text:
                docs.append({"source": path.name, "text": text})
        except Exception:
            continue
    return docs


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            start = 0
        if end >= len(text):
            break
    return chunks


class DocumentIndex:
    """Simple TF-IDF index over document chunks (no heavy native deps)."""

    def __init__(self):
        self.chunks: List[Dict[str, str]] = []
        self._vectorizer = None
        self._matrix = None
        self._build()

    def _build(self):
        raw_docs = _load_documents()
        self.chunks = []
        for doc in raw_docs:
            for i, ch in enumerate(_chunk_text(doc["text"])):
                self.chunks.append(
                    {"source": doc["source"], "chunk_id": i, "text": ch}
                )
        if not self.chunks:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
            corpus = [c["text"] for c in self.chunks]
            self._matrix = self._vectorizer.fit_transform(corpus)
        except Exception:
            self._vectorizer = None
            self._matrix = None

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []
        if self._vectorizer is not None and self._matrix is not None:
            import numpy as np
            q = self._vectorizer.transform([query])
            scores = (self._matrix @ q.T).toarray().ravel()
            idx = np.argsort(scores)[::-1][:top_k]
            results = []
            for i in idx:
                if scores[i] <= 0:
                    continue
                item = dict(self.chunks[i])
                item["score"] = float(scores[i])
                results.append(item)
            return results
        # Keyword fallback
        words = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored = []
        for c in self.chunks:
            cw = set(re.findall(r"[a-z0-9]+", c["text"].lower()))
            overlap = len(words & cw)
            if overlap:
                scored.append((overlap, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, c in scored[:top_k]:
            item = dict(c)
            item["score"] = float(score)
            out.append(item)
        return out


_INDEX: DocumentIndex | None = None


def get_index() -> DocumentIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = DocumentIndex()
    return _INDEX


def run_vector_fallback_agent(question: str) -> dict:
    """
    Retrieve document chunks and synthesize an answer.
    Used when SQL path fails or returns no rows.
    """
    index = get_index()
    hits = index.search(question, top_k=4)

    if not hits:
        return {
            "success": False,
            "answer": (
                "I could not answer from the database or the document knowledge base. "
                "Try rephrasing or ask about customers, employees, projects, or sales."
            ),
            "sources": [],
            "chunks": [],
        }

    context = "\n\n".join(
        f"[{h['source']}] {h['text']}" for h in hits
    )
    system = (
        "You are a helpful assistant. Answer the user question using ONLY the provided "
        "document context. If the context is insufficient, say what is missing. "
        "Be concise (2-5 sentences)."
    )
    user = f"Question: {question}\n\nContext:\n{context}"
    raw = call_llm(system, user, temperature=0.2)

    if raw.startswith("[NO_LLM]") or raw.startswith("[LLM_ERROR]"):
        # Stitch a simple extractive answer
        answer = (
            "Here is what I found in internal documents:\n"
            + "\n".join(f"- ({h['source']}) {h['text'][:220]}..." for h in hits)
        )
    else:
        answer = raw

    return {
        "success": True,
        "answer": answer,
        "sources": list({h["source"] for h in hits}),
        "chunks": [
            {"source": h["source"], "score": h.get("score"), "text": h["text"][:300]}
            for h in hits
        ],
    }
