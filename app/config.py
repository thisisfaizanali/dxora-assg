from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    http_timeout_seconds: float = 15.0
    telegraph_access_token: str = ""
    telegraph_author_name: str = "Automated Posting"
    ntfy_topic: str = "dxora-automated-posting-demo"


settings = Settings()
