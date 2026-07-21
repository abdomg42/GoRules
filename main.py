from fastapi import FastAPI
from src.ingestion.parsing import 
from src.ingestion.embedding import EmbeddingClient, EmbeddingAgent
from src.ingestion.chunking import Chunk 
from src.store import OllamaEmbeddingFunction

app = FastAPI()

_parser = 