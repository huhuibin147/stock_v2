from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./data/stock_v2.db"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    log_level: str = "INFO"
    backend_port: int = 38080

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
