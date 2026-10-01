from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    xai_api_key: str = ""
    xai_model: str = "grok-4.6"
    xai_base_url: str = "https://api.x.ai"
    max_upload_mb: int = 40
    # Time between streamed chunks. Long reasoning models can sit quiet, then
    # emit tokens; streaming keeps this from being one 600s wait for the body.
    request_timeout_seconds: float = 1200.0
    file_ttl_seconds: int = 3600
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    return Settings()
