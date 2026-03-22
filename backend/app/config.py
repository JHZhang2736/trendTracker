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

    # Search (for deep analysis)
    search_provider: str = "duckduckgo"

    # Deep analysis
    deep_analysis_auto_ratio: float = 0.3  # analyze top 30% of relevant keywords
    deep_analysis_auto_max: int = 10  # hard cap per collection run
    deep_analysis_cooldown_hours: int = 24  # skip re-analysis within this window

    # Scheduler — global default and per-platform overrides
    collect_cron: str = "0 6 * * *"
    weibo_cron: str = "0 */2 * * *"  # every 2 hours (hot search has short half-life)
    google_cron: str = ""  # empty = use collect_cron
    tiktok_cron: str = "0 */6 * * *"  # every 6 hours

    # Signal-driven AI analysis
    signal_auto_analyze_limit: int = 3  # max signals to auto-analyze per detection run

    # AI relevance filter
    relevance_filter_enabled: bool = True
    user_profile: str = ""

    # TikTok
    tiktok_cookie: str = ""  # Paste browser Cookie header from ads.tiktok.com session

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
