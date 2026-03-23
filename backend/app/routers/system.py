"""System router — configuration status and admin operations."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings
from app.services.deep_analysis import get_show_business, set_show_business
from app.services.platform_state import get_all_platform_states, set_platform_enabled

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
            "show_business": get_show_business(),
        },
        "platforms": get_all_platform_states(),
    }


class PlatformToggleRequest(BaseModel):
    platform: str
    enabled: bool


@router.put("/platforms", summary="切换平台信息源开关")
async def toggle_platform(body: PlatformToggleRequest) -> dict:
    """Enable or disable a platform data source."""
    set_platform_enabled(body.platform, body.enabled)
    return {"platform": body.platform, "enabled": body.enabled}


class ShowBusinessRequest(BaseModel):
    show: bool


@router.put("/deep-analysis-mode", summary="切换是否显示商业分析")
async def update_show_business(body: ShowBusinessRequest) -> dict:
    """Toggle whether business analysis section is displayed in deep analysis cards."""
    set_show_business(body.show)
    return {"show_business": body.show}
