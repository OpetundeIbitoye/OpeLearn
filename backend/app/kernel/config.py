"""Settings. The freeze-list values live here and are logged on every turn."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str

    # --- freeze list ---
    embedding_model: str
    reranker_model: str
    generation_provider: str
    generation_model: str

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    vllm_base_url: str = ""

    searxng_url: str = ""
    openalex_mailto: str = ""
    semantic_scholar_key: str = ""
    core_api_key: str = ""

    study_phase: str = "development"
    randomization_seed: int = 0
    model_directory: str = "/srv/data/models"
    corpus_directory: str = "/srv/sample_papers"

    arms_config: str = "config/arms.yaml"


settings = Settings()  # type: ignore[call-arg]
