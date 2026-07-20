
import json 
from urllib import error, request

from src.config import OLLAMA_BASE_URL, EMBEDDING_MODEL


class EmbeddingClient:

    def __init__(self):
        self.ollama_base_url = OLLAMA_BASE_URL.rconfigstrip("/")
        self.model = EMBEDDING_MODEL

    def embed_batch(self, texts):

        if not texts:
            return []
        
        playload: dict[str, object]= {
            "model": self.model,
            "input": texts,
        }

        req = request.Request(
            url=f"{self.ollama_base_url}/api/embed",
            data=json.dumps(playload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try :
            with request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as e:
            raise RuntimeError(f"HTTP error: {e.code} - {e.reason}")
        except error.URLError as e:
            raise RuntimeError(f"URL error: {e.reason}")

        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected response format: {data}")
        embeddings = data.get("embeddings")
        
        if isinstance(embeddings, list):
            return [list(map(float, emb)) for emb in embeddings if isinstance(emb, list)]
        embeddings = data.get("embedding")
        if isinstance(embeddings, list):
            return list(map(float, embeddings))
        
        raise RuntimeError(f"Unexpected response format: {data}")
    
class EmbeddingAgent:
    pass
