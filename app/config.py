from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API keys
    anthropic_api_key: str
    voyage_api_key: str = ""

    # App config
    embedding_provider: str = "voyage"
    claude_model: str = "claude-sonnet-5"
    top_k: int = 5

    # Paths
    chroma_dir: str = "data/chroma"
    upload_dir: str = "data/uploads"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_chroma_path(self) -> Path:
        return Path(self.chroma_dir).resolve()

    def get_upload_path(self) -> Path:
        return Path(self.upload_dir).resolve()


settings = Settings()
