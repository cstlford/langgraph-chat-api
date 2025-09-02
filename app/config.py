from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "Default App"
    app_version: str = "0.1.0"
    interpreter_url: str = "Unkown"


settings = Settings()


class DatabaseSettings(BaseSettings):
    orchestrator_database: str = "unknown"
    snowflake_private_key: str = "unknown"
    snowflake_pass: str = "unknown"
    warehouse: str = "unknown"
    account: str = "unknown"
    snowflake_user: str = "unknown"


db_settings = DatabaseSettings()


class VectorStoreConfig(BaseModel):
    collection_name: str = "snowflake_schema"
    embedding_model: str = "text-embedding-3-small"
    schema_files: list[str] = [
        "dm_bi.json",
        "isp.json",
    ]  # changes here must also be made to schema_retriever tool
    schema_dir: str = "app/database/vector_database/models"
    persist_dir: str = "app/database/vector_database/chroma_db"


vector_store_config = VectorStoreConfig()
