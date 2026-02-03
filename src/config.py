from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCREENING_", env_file=".env")

    torre_base_url: str = "https://torre.ai"
    torre_timeout: float = 5.0
    torre_retries: int = 1
