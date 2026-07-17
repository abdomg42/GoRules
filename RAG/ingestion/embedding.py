
import json 
from urllib import error, request

from src.config import settings


class EmbeddingClient:

    def __init__(self):
        self.ollama_base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.embedding_model

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

        