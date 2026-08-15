from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    openai_api_key: str
    frontend_url: str = "http://localhost:3000"
    sse_poll_interval_seconds: float = 1.0
    sse_heartbeat_interval_seconds: float = 20.0
    sse_max_connection_seconds: float = 1800.0
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
