from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field(default="Обозреватель Технической Документации API", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")

    opensearch_host: str = Field(default="http://localhost:9200", alias="OPENSEARCH_HOST")
    opensearch_index: str = Field(default="telecom_docs_v1", alias="OPENSEARCH_INDEX")
    opensearch_username: str = Field(default="", alias="OPENSEARCH_USERNAME")
    opensearch_password: str = Field(default="", alias="OPENSEARCH_PASSWORD")
    storage_db_path: str = Field(
        default=str(Path(__file__).resolve().parents[1] / "data" / "library.db"),
        alias="STORAGE_DB_PATH",
    )


settings = Settings()
