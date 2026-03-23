"""System router — configuration status and admin operations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.services.deep_analysis import get_analysis_mode, set_analysis_mode

router = APIRouter()


@router.get("/config", summary="查询系统配置就绪状态（不含原始密钥）")
async def get_system_config() -> dict:
    """Return the configuration readiness of each subsystem.

    Raw secret values are never exposed — only boolean flags and non-sensitive strings.
    """
    return {
        "ai": {
            "provider": settings.llm_provider,
            "configured": bool(settings.minimax_api_key and settings.minimax_group_id),
        },
        "tiktok": {
            "configured": bool(settings.tiktok_cookie),
        },
        "scheduler": {
            "collect_cron": settings.collect_cron,
        },
        "email": {
            "configured": bool(
                settings.smtp_user and settings.smtp_password and settings.alert_email_to
            ),
            "smtp_host": settings.smtp_host,
            "recipient": settings.alert_email_to or None,
        },
        "deep_analysis": {
            "mode": get_analysis_mode(),
        },
    }


class AnalysisModeRequest(BaseModel):
    mode: str


@router.put("/deep-analysis-mode", summary="切换深度分析模式（business/news）")
async def update_analysis_mode(body: AnalysisModeRequest) -> dict:
    """Toggle deep analysis mode between 'business' and 'news' at runtime."""
    if body.mode not in ("business", "news"):
        raise HTTPException(status_code=400, detail="mode must be 'business' or 'news'")
    set_analysis_mode(body.mode)
    return {"mode": body.mode}
