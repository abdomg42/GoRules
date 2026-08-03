# uvicorn main:app --reload

import json
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
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
from db import delete_messages, get_messages, init_db, save_message  # noqa: E402

SUPPORTED_SUFFIXES = {".pdf", ".docx"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise les ressources persistantes au demarrage du serveur."""
    init_db()
    yield


app = FastAPI(title="GoRules API", version="1.0.0", lifespan=lifespan)

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


class Message(BaseModel):
    role: str
    content: str
    sources: list[Source] = []
    created_at: datetime | None = None


class MessageList(BaseModel):
    messages: list[Message]


class SaveMessageRequest(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)
    sources: list[Source] = []


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
        save_message(project_id, "user", payload.question)
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
    save_message(
        project_id,
        "assistant",
        answer,
        sources=[s.model_dump() for s in sources],
    )
    return QueryResponse(answer=answer, sources=sources)


@app.post("/project/{project_id}/query/stream")
def query_project_stream(project_id: str, payload: QueryRequest):
    """Variante streamante de /query : evenements NDJSON (sources, token, error).

    L'utilisateur et la reponse complete sont persistes en base.
    """
    try:
        save_message(project_id, "user", payload.question)
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
        pieces: list[str] = []
        try:
            for piece in ask_stream(payload.question, chunks):
                pieces.append(piece)
                yield json.dumps({"type": "token", "text": piece}, ensure_ascii=False) + "\n"
        except Exception as exc:
            yield json.dumps({"type": "error", "detail": str(exc)}, ensure_ascii=False) + "\n"
        finally:
            answer = "".join(pieces)
            if answer:
                save_message(project_id, "assistant", answer, sources=sources)

@app.get("/project/{project_id}/messages", response_model=MessageList)
def list_messages(project_id: str, limit: int = 100) -> MessageList:
    """Retourne l'historique persistant des messages d'un projet."""
    rows = get_messages(project_id, limit=limit)
    messages = []
    for msg in rows:
        sources = [Source(**s) for s in (msg.sources or [])]
        messages.append(
            Message(
                role=msg.role,
                content=msg.content,
                sources=sources,
                created_at=msg.created_at,
            )
        )
    return MessageList(messages=messages)


@app.post("/project/{project_id}/messages", status_code=201)
def create_message(project_id: str, payload: SaveMessageRequest) -> dict:
    """Endpoint explicite pour sauvegarder un message (utilise par le frontend)."""
    save_message(
        project_id,
        payload.role,
        payload.content,
        sources=[s.model_dump() for s in payload.sources],
    )
    return {"status": "ok"}


@app.delete("/project/{project_id}/messages", status_code=204)
def clear_messages(project_id: str) -> None:
    """Supprime l'historique d'un projet."""
    delete_messages(project_id)
    return None
