import os

from dotenv import load_dotenv

load_dotenv()

# Configuration locale via Ollama (pas de cle API externe)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral:7b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_data")

# Parametres de chunking (en mots, approximation simple ~1.3 mot/token en francais)
CHUNK_SIZE_WORDS = 350
CHUNK_OVERLAP_WORDS = 50
