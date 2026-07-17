from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

    #llm 
    ollama_base_url = "http://localhost:11434"
    llm_model_reasoning = "mistral:7b"
    llm_model_light = "mistral:7b"
    
    #Qdrant 
    qdrant_url = "http://localhost:6333"
    qdrant_collection = "documents"

    #Neo4j
    neo4j_url = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password123"

    #Redis 
    redis_url = "redis://localhost:6379"

    #Postgres
    database_url = "postgresql://postgres:password@localhost:5432/mydatabase"

    #Embeddings
    embedding_model = "mxbai-embed-large"
    embedding_dimension= 1024

    # Chunking
    chunk_size_tokens = 500
    chunk_overlap_tokens = 75


settings = Settings()