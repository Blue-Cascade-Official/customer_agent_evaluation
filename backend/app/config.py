from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://internee:internee@localhost:5432/internee_eval"
    postgres_url: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = "agent_8801m754zcqefqatys0hhnr0x82s"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    gcs_bucket: str = ""
    gcs_project_id: str = ""
    google_application_credentials: str = ""
    google_credentials_json: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    cors_origins: str = (
        "http://localhost:5173,"
        "https://customer-agent-eval-web.onrender.com,"
        "https://evaluation.aibluecascade.org"
    )
    local_audio_dir: str = "./data/audio"
    local_knowledge_dir: str = "./data/knowledge"
    embedding_dimensions: int = 1536
    rag_top_k: int = 8

    @property
    def cors_origin_list(self) -> list[str]:
        # Browsers never send a trailing slash on Origin; normalize env typos.
        origins = [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]
        # Always allow known production frontends even if env is incomplete.
        for required in (
            "https://customer-agent-eval-web.onrender.com",
            "https://evaluation.aibluecascade.org",
            "http://localhost:5173",
        ):
            if required not in origins:
                origins.append(required)
        return origins

    @property
    def use_gcs(self) -> bool:
        return bool(self.gcs_bucket)

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    import os

    if settings.google_application_credentials:
        cred_path = Path(settings.google_application_credentials)
        if cred_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path.resolve())
    if settings.gcs_project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.gcs_project_id)
    return settings

