"""Tests for SQLAlchemy model definitions (import and attribute checks)."""
import pytest

from app.models import (
    AIInsight,
    AlertLog,
    CollectorLog,
    DailyBrief,
    Keyword,
    KeywordAlert,
    Platform,
    Trend,
)


def test_platform_tablename():
    assert Platform.__tablename__ == "platforms"


def test_trend_tablename():
    assert Trend.__tablename__ == "trends"


def test_keyword_tablename():
    assert Keyword.__tablename__ == "keywords"


def test_keyword_alert_tablename():
    assert KeywordAlert.__tablename__ == "keyword_alerts"


def test_ai_insight_tablename():
    assert AIInsight.__tablename__ == "ai_insights"


def test_daily_brief_tablename():
    assert DailyBrief.__tablename__ == "daily_briefs"


def test_alert_log_tablename():
    assert AlertLog.__tablename__ == "alert_logs"


def test_collector_log_tablename():
    assert CollectorLog.__tablename__ == "collector_logs"


def test_platform_columns():
    cols = {c.name for c in Platform.__table__.columns}
    assert {"id", "name", "slug", "is_active", "config_json", "created_at"} <= cols


def test_trend_columns():
    cols = {c.name for c in Trend.__table__.columns}
    assert {"id", "platform", "keyword", "rank", "heat_score", "collected_at", "url"} <= cols


def test_keyword_columns():
    cols = {c.name for c in Keyword.__table__.columns}
    assert {"id", "keyword", "category", "is_active", "created_at"} <= cols


def test_keyword_alert_columns():
    cols = {c.name for c in KeywordAlert.__table__.columns}
    assert {"id", "keyword_id", "threshold", "notify_email", "is_active"} <= cols


def test_ai_insight_columns():
    cols = {c.name for c in AIInsight.__table__.columns}
    assert {"id", "trend_id", "insight_type", "content", "model", "created_at"} <= cols


def test_daily_brief_columns():
    cols = {c.name for c in DailyBrief.__table__.columns}
    assert {"id", "date", "content", "model", "created_at"} <= cols


def test_alert_log_columns():
    cols = {c.name for c in AlertLog.__table__.columns}
    assert {"id", "keyword_id", "triggered_at", "matched_keywords", "notified"} <= cols


def test_collector_log_columns():
    cols = {c.name for c in CollectorLog.__table__.columns}
    assert {"id", "platform", "status", "records_count", "error_msg", "run_at"} <= cols
