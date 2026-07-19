import json
import urllib.error
import urllib.request

import chromadb

from config import CHROMA_DIR, EMBEDDING_MODEL, OLLAMA_BASE_URL
from ingestion.chunking import Chunk

class OllamaEmbeddingFunction:
    def __init__(self, model_name: str, base_url: str) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def _request_embedding(self, text: str) -> list[float]:
        for endpoint in ("/api/embed", "/api/embeddings"):
            payload = {"model": self.model_name, "input": text}
            request = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = json.load(response)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    continue
                detail = exc.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"Erreur Ollama embeddings sur {endpoint}: {detail}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(
                    f"Impossible de joindre Ollama embeddings sur {self.base_url}: {exc.reason}"
                ) from exc
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Reponse Ollama embeddings invalide depuis {endpoint}: {exc}") from exc

            if "embedding" in data:
                return data["embedding"]
            if "embeddings" in data:
                embeddings = data["embeddings"]
                if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
                    return embeddings[0]
                if isinstance(embeddings, list) and len(embeddings) == 1:
                    return embeddings[0]
            raise RuntimeError(f"Format de reponse Ollama embeddings inattendu: {data}")

        raise RuntimeError(f"Aucune endpoint Ollama embeddings compatible trouvee sur {self.base_url}")

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._request_embedding(text) for text in input]


_embedding_fn = OllamaEmbeddingFunction(model_name=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
_client = chromadb.PersistentClient(path=CHROMA_DIR)


def get_collection(project: str):
    return _client.get_or_create_collection(name=project, embedding_function=_embedding_fn)


def add_chunks(project: str, chunks: list[Chunk]) -> None:
    if not chunks:
        return
    collection = get_collection(project)
    collection.add(
        ids=[c.chunk_id for c in chunks],
        documents=[c.content for c in chunks],
        metadatas=[
            {"document_name": c.document_name, "section_label": c.section_label} for c in chunks
        ],
    )


def search(project: str, question: str, top_k: int = 6) -> list[dict]:
    collection = get_collection(project)
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[question], n_results=min(top_k, collection.count()))
    hits = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        hits.append({"content": doc, **meta})
    return hits
