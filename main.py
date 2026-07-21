from fastapi import FastAPI
from src.ingestion.parsing import Parser
from src.ingestion.embedding import EmbeddingClient, EmbeddingAgent
from src.ingestion.chunking import Chunker
from src.store import OllamaEmbeddingFunction

app = FastAPI()

_parser = Parser()
_chunker = Chunker()
_embedding = EmbeddingAgent(embedding_client=EmbeddingClient())
