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
    deep_analysis_mode: str = "business"  # "business" or "news"

    # DailyHot API (self-hosted aggregator)
    dailyhot_api_url: str = "http://localhost:6688"

    # Scheduler — global default and per-platform overrides (empty = use collect_cron)
    collect_cron: str = "0 6 * * *"
    weibo_cron: str = "0 */2 * * *"
    douyin_cron: str = ""
    toutiao_cron: str = ""
    qq_news_cron: str = ""
    netease_news_cron: str = ""
    sina_news_cron: str = ""
    nytimes_cron: str = ""
    zhihu_cron: str = ""
    zhihu_daily_cron: str = ""
    tieba_cron: str = ""
    hupu_cron: str = ""
    douban_group_cron: str = ""
    kr36_cron: str = ""
    producthunt_cron: str = ""
    github_cron: str = ""
    hackernews_cron: str = ""
    bilibili_cron: str = ""
    kuaishou_cron: str = ""
    smzdm_cron: str = ""
    coolapk_cron: str = ""
    yystv_cron: str = ""

    # Platform enable/disable (PLATFORM_XXX=false in .env to disable by default)
    platform_weibo: bool = True
    platform_douyin: bool = True
    platform_toutiao: bool = True
    platform_qq_news: bool = True
    platform_netease_news: bool = True
    platform_sina_news: bool = True
    platform_nytimes: bool = True
    platform_zhihu: bool = True
    platform_zhihu_daily: bool = True
    platform_tieba: bool = True
    platform_hupu: bool = True
    platform_douban_group: bool = True
    platform_36kr: bool = True
    platform_producthunt: bool = True
    platform_github: bool = True
    platform_hackernews: bool = True
    platform_bilibili: bool = True
    platform_kuaishou: bool = True
    platform_smzdm: bool = True
    platform_coolapk: bool = True
    platform_yystv: bool = True

    # Signal-driven AI analysis
    signal_auto_analyze_limit: int = 3  # max signals to auto-analyze per detection run

    # AI relevance filter
    relevance_filter_enabled: bool = True
    user_profile: str = ""

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

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
