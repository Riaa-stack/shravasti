from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "super-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Postgres
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "scholarforge"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "Riya@9359"

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "/data/chroma"

    # OpenRouter (LLM)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    LLM_MODEL_LITERATURE_REVIEW: str = "deepseek/deepseek-chat"
    LLM_MODEL_METHODOLOGY: str = "deepseek/deepseek-chat"
    LLM_MODEL_GAP: str = "deepseek/deepseek-r1"
    LLM_MODEL_TREND: str = "qwen/qwen-2.5-72b-instruct"
    LLM_MODEL_IDEA: str = "deepseek/deepseek-r1"
    LLM_MODEL_CITATION: str = "deepseek/deepseek-chat"
    LLM_MODEL_CHAT: str = "deepseek/deepseek-chat"
    LLM_MODEL_DIFFICULTY: str = "google/gemma-3-27b-it"

    # Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_FALLBACK_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # OCR / NLP
    EASYOCR_LANGS: str = "en"
    GROBID_ENABLED: bool = False
    GROBID_URL: str = "http://grobid:8070"

    # External Research APIs
    CROSSREF_ENABLED: bool = True
    CROSSREF_MAILTO: str = ""
    SEMANTIC_SCHOLAR_API_KEY: str = ""
    ARXIV_ENABLED: bool = True
    OPENALEX_ENABLED: bool = True
    OPENALEX_MAILTO: str = ""

    # Storage
    PAPERS_STORAGE_DIR: str = "/data/papers"
    EXPORTS_STORAGE_DIR: str = "/data/exports"

    @property
    def DATABASE_URL(self) -> str:
        """
        Build the PostgreSQL URL safely.

        SQLAlchemy URL.create() handles special characters
        in the PostgreSQL username/password correctly.
        """
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()