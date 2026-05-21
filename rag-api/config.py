from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embed_model: str = "nomic-embed-text"

    chromadb_host: str = "chromadb"
    chromadb_port: int = 8000
    chromadb_collection: str = "filip_knowledge"

    knowledge_base_dir: str = "/app/knowledge-base"

    cors_origins: list[str] = ["https://filipcsupka.online", "https://www.filipcsupka.online"]

    # RAG retrieval
    top_k: int = 4
    chunk_size: int = 500
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
