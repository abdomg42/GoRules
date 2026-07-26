# uvicorn main:app --reload

import json
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"


sys.path.insert(0, str(SRC_DIR))


load_dotenv(ROOT_DIR / ".env")
_chroma_dir = Path(os.getenv("CHROMA_DIR", "./chroma_data"))
if not _chroma_dir.is_absolute():
    _chroma_dir = SRC_DIR / _chroma_dir
os.environ["CHROMA_DIR"] = str(_chroma_dir)

from agents.agent import ask, ask_stream  # noqa: E402
from ingestion.chunking import Chunker  # noqa: E402
from ingestion.parsing import Parser  # noqa: E402
from store import add_chunks, list_projects, search  # noqa: E402

SUPPORTED_SUFFIXES = {".pdf", ".docx"}

app = FastAPI(title="GoRules API", version="1.0.0")

_chunker = Chunker()


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)


class Source(BaseModel):
    document_name: str
    section_label: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]


def _index_document(project_id: str, filename: str, data: bytes) -> dict:
    """Parse, chunk puis indexe un document dans la collection du projet."""
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporte: {suffix or '(aucun)'}. Formats acceptes: PDF, DOCX.",
        )
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        document_name = Path(filename).stem
        sections = Parser(tmp_path).parse_document()
        chunks = _chunker.chunk_sections(
            sections, document_name=document_name, project_id=project_id
        )
        add_chunks(project_id, chunks)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Echec de l'indexation: {exc}"
        ) from exc
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

    return {
        "document_name": document_name,
        "filename": filename,
        "chunks": len(chunks),
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/projects")
def projects() -> dict:
    return {"projects": list_projects()}


@app.post("/project/{project_id}/documents")
async def upload_document(project_id: str, filename: str, request: Request) -> dict:
    """Indexe un document PDF/DOCX envoye en corps brut (nom via ?filename=)."""
    data = await request.body()
    return await run_in_threadpool(_index_document, project_id, filename, data)


@app.post("/project/{project_id}/query", response_model=QueryResponse)
def query_project(project_id: str, payload: QueryRequest) -> QueryResponse:
    try:
        chunks = search(project_id, payload.question, top_k=payload.top_k)
        answer = ask(payload.question, chunks)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sources = [
        Source(
            document_name=str(chunk.get("document_name", "?")),
            section_label=str(chunk.get("section_label", "?")),
        )
        for chunk in chunks
    ]
    return QueryResponse(answer=answer, sources=sources)


@app.post("/project/{project_id}/query/stream")
def query_project_stream(project_id: str, payload: QueryRequest):
    """Variante streamante de /query : evenements NDJSON (sources, token, error)."""
    try:
        chunks = search(project_id, payload.question, top_k=payload.top_k)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    sources = [
        {
            "document_name": str(chunk.get("document_name", "?")),
            "section_label": str(chunk.get("section_label", "?")),
        }
        for chunk in chunks
    ]

    def event_stream():
        yield json.dumps({"type": "sources", "sources": sources}, ensure_ascii=False) + "\n"
        try:
            for piece in ask_stream(payload.question, chunks):
                yield json.dumps({"type": "token", "text": piece}, ensure_ascii=False) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
