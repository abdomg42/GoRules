from fastapi import FastAPI,APIRouter,Upload_file
import tempfile
from pathlib import Path
import shutil

from src.ingestion.parsing import Parser
from src.ingestion.embedding import EmbeddingClient, EmbeddingAgent
from src.ingestion.chunking import Chunker
from src.store import OllamaEmbeddingFunction

app = FastAPI()
router = APIRouter()
_parser = Parser()
_chunker = Chunker()
_embedding = EmbeddingAgent(embedding_client=EmbeddingClient())

@app.get("/health")
def status():
    return {"status": "ok"}

@router.post("/project/{project_id}/documents")
async def upload_document(project_id: str, file: Upload_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    document_id = Path(temp_path).stem
    sections = _parser.parse_document(temp_path)
    chunks = _chunker.chunk_sections(sections, document_id=document_id, project_id=project_id)
    _embedding.embed_and_index(chunks)
    return {
        "documents_id": document_id,
        "filename":file.filename,
        "chunks":len(chunks)
    }

@router.post("/project/{project_id}/query")
async def query_project(project_id: str, query: str):
    embedding_function= OllamaEmbeddingFunction()
    query = embedding_function.embed_query(query)

