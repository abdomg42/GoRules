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

    def name(self) -> str:
        return f"ollama:{self.model_name}"

    def _shrink_text_for_context(self, text: str) -> str:
        words = text.split()
        if len(words) > 1:
            return " ".join(words[: max(1, len(words) // 2)])
        if len(text) > 200:
            return text[: max(100, len(text) // 2)]
        return text

    def _request_embedding(self, text: str) -> list[float]:
        candidate_text = text
        for endpoint in ("/api/embed", "/api/embeddings"):
            while True:
                payload = {"model": self.model_name, "input": candidate_text}
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
                        break
                    detail = exc.read().decode("utf-8", errors="ignore")
                    if exc.code == 400 and "context length" in detail.lower():
                        reduced_text = self._shrink_text_for_context(candidate_text)
                        if reduced_text == candidate_text:
                            raise RuntimeError(
                                f"Erreur Ollama embeddings sur {endpoint}: {detail}"
                            ) from exc
                        candidate_text = reduced_text
                        continue
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

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self.__call__(input)

    def embed_query(self, input: str | list[str]) -> list[list[float]]:
        if isinstance(input, str):
            return [self._request_embedding(input)]
        return self.__call__(input)


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
    try:
        results = collection.query(query_texts=[question], n_results=min(top_k, collection.count()))
        hits = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            hits.append({"content": doc, **meta})
        return hits
    except Exception:
        fallback = collection.get(limit=min(top_k, collection.count()), include=["documents", "metadatas"])
        documents = fallback.get("documents") or []
        metadatas = fallback.get("metadatas") or []
        hits = []
        for doc, meta in zip(documents, metadatas):
            if isinstance(doc, str) and isinstance(meta, dict):
                hits.append({"content": doc, **meta})
        return hits
