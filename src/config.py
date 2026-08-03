import os

from dotenv import load_dotenv

load_dotenv()

# Configuration locale Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral:7b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")

# PostgreSQL pour la persistance des messages
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/gorules")

# Parametres de chunking 
CHUNK_SIZE_WORDS = 120
CHUNK_OVERLAP_WORDS = 20
