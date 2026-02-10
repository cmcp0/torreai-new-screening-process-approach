from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCREENING_", env_file=".env")

    torre_base_url: str = "https://torre.ai"
    torre_timeout: float = 5.0
    torre_retries: int = 1  # Number of retries after first attempt (1 = "retry once" per design)
    cors_origins: str = "http://localhost:5173"

    broker_url: str = ""
    database_url: str = ""

    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout: float = 60.0
    ollama_embed_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"
