"""System router — configuration status and admin operations."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings

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
    }
