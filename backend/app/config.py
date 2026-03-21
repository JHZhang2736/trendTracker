from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root .env (works whether you run from backend/ or project root)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_name: str = "trendtracker"
    db_user: str = "root"
    db_password: str = ""

    # AI
    llm_provider: str = "minimax"
    minimax_api_key: str = ""
    minimax_group_id: str = ""

    # Scheduler
    collect_cron: str = "0 6 * * *"

    # TikTok
    tiktok_cookie: str = ""  # Paste browser Cookie header from ads.tiktok.com session

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_to: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")


settings = Settings()
