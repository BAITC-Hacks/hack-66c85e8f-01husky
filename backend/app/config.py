from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "Meeting Protocol API"
    debug: bool = False
    secret_key: str = "change-me-in-env"
    access_token_days: int = 7
    cookie_secure: bool = False

    database_url: str = "postgresql+psycopg://protocol:protocol@localhost:5432/protocol"
    redis_url: str = "redis://localhost:6379/0"

    data_dir: Path = BACKEND_DIR / "data"
    outbox_dir: Path = BACKEND_DIR / "outbox"

    pipeline_fake: bool = True
    stt_backend: str = "local"
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:14b"
    ollama_url: str = "http://localhost:11434"
    hf_token: str | None = None
    nvidia_api_key: str | None = None
    openai_api_key: str | None = None

    due_soon_hours: int = 24
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.audio_dir.mkdir(parents=True, exist_ok=True)
    s.outbox_dir.mkdir(parents=True, exist_ok=True)
    return s
