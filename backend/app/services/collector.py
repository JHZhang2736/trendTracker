"""Collector service — run all collectors and persist results to DB."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import registry
from app.models.platform import Platform
from app.models.trend import Trend

logger = logging.getLogger(__name__)

# Number of concurrent workers pulling from the collection queue.
_NUM_WORKERS = 5


async def _score_new_keywords(
    db: AsyncSession,
    hour_start: datetime,
    hour_end: datetime,
) -> dict[str, dict]:
    """Score newly collected keywords for personal relevance via AI.

    Returns the scores dict for use by downstream pipeline stages (e.g. deep analysis).
    """
    from app.config import settings as app_settings
    from app.services.relevance import score_relevance

    # Fetch keywords from the current hour that have no relevance score yet
    result = await db.execute(
        select(Trend).where(
            Trend.collected_at >= hour_start,
            Trend.collected_at < hour_end,
            Trend.relevance_score.is_(None),
        )
    )
    trends = result.scalars().all()
    if not trends:
        return {}

    # Deduplicate keywords for the API call (preserve insertion order)
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for t in trends:
        if t.keyword not in seen:
            seen.add(t.keyword)
            unique_keywords.append(t.keyword)
    logger.info("Scoring relevance for %d unique keywords", len(unique_keywords))

    try:
        scores = await score_relevance(unique_keywords, app_settings.user_profile)
    except Exception:
        logger.exception("Relevance scoring failed, skipping")
        return {}

    # Apply scores back to trend records
    unmatched = set()
    for trend in trends:
        info = scores.get(trend.keyword)
        if info:
            trend.relevance_score = info["score"]
            trend.relevance_label = info["label"]
            trend.relevance_reason = info.get("reason", "")
        else:
            unmatched.add(trend.keyword)

    if unmatched:
        logger.warning(
            "Relevance: %d keywords got no score from LLM: %s",
            len(unmatched),
            list(unmatched)[:10],
        )

    await db.commit()
    relevant_count = sum(1 for t in trends if t.relevance_label == "relevant")
    logger.info(
        "Relevance scoring complete: %d/%d marked relevant",
        relevant_count,
        len(trends),
    )
    return scores


async def _ensure_platform(db: AsyncSession, slug: str) -> int:
    """Get or create a platform record; return its id."""
    result = await db.execute(select(Platform).where(Platform.slug == slug))
    platform = result.scalar_one_or_none()
    if platform is None:
        platform = Platform(name=slug.capitalize(), slug=slug)
        db.add(platform)
        await db.flush()
    return platform.id


# ---------------------------------------------------------------------------
# Queue-based collection helpers
# ---------------------------------------------------------------------------

_CollectResult = tuple[str, list[dict], str | None]  # (slug, records, error)


async def _collect_one(platform_slug: str) -> _CollectResult:
    """Run a single collector and return (platform_slug, records, error). Never raises."""
    collector_cls = registry.get(platform_slug)
    try:
        records = await collector_cls().collect()
        return platform_slug, records or [], None
    except Exception as exc:  # noqa: BLE001
        logger.error("_collect_one[%s]: failed — %s: %s", platform_slug, type(exc).__name__, exc)
        return platform_slug, [], str(exc)


async def _queue_worker(
    queue: asyncio.Queue[str],
    results: list[_CollectResult],
) -> None:
    """Worker that pulls platform slugs from *queue* and collects them."""
    while True:
        slug = await queue.get()
        try:
            result = await _collect_one(slug)
            results.append(result)
        finally:
            queue.task_done()


async def _run_collection_queue(platforms: list[str]) -> list[_CollectResult]:
    """Enqueue all *platforms* and collect via a fixed-size worker pool."""
    queue: asyncio.Queue[str] = asyncio.Queue()
    results: list[_CollectResult] = []

    for slug in platforms:
        queue.put_nowait(slug)

    workers = [asyncio.create_task(_queue_worker(queue, results)) for _ in range(_NUM_WORKERS)]
    await queue.join()

    for w in workers:
        w.cancel()

    return results


async def _queue_worker_stream(
    queue: asyncio.Queue[str],
    out: asyncio.Queue[_CollectResult],
) -> None:
    """Worker that collects and pushes results to *out* for streaming."""
    while True:
        slug = await queue.get()
        try:
            result = await _collect_one(slug)
            await out.put(result)
        finally:
            queue.task_done()


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


async def run_all_collectors(
    db: AsyncSession,
    platforms: list[str] | None = None,
) -> dict:
    """Run collectors via a queue-based worker pool, persist results, return summary.

    Args:
        db: async database session.
        platforms: optional list of platform slugs to collect.
                   If None, all enabled platforms are collected.

    Each platform uses replace-by-hour semantics: existing records for the same
    platform within the current clock-hour are deleted before inserting the fresh
    batch.  This prevents duplicate rows when collection is triggered more than
    once within the same hour (e.g. manual + scheduled), while preserving all
    cross-hour historical data for trend charts.

    Returns a dict with ``status`` and ``records_count``.
    """
    from app.services.platform_state import get_enabled_platforms

    if platforms is None:
        platforms = get_enabled_platforms()
    else:
        enabled = set(get_enabled_platforms())
        platforms = [p for p in platforms if p in enabled]

    # Current hour bucket (naive UTC, matching DB storage)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    # Collect via queue workers
    results = await _run_collection_queue(platforms)

    total_records = 0
    platform_results = []
    for platform_slug, records, error in results:
        platform_results.append({"platform": platform_slug, "count": len(records), "error": error})
        if not records:
            continue

        # Replace-by-hour: remove stale records in the current hour bucket
        await db.execute(
            delete(Trend).where(
                Trend.platform == platform_slug,
                Trend.collected_at >= hour_start,
                Trend.collected_at < hour_end,
            )
        )

        platform_id = await _ensure_platform(db, platform_slug)
        for rec in records:
            db.add(
                Trend(
                    platform_id=platform_id,
                    platform=rec["platform"],
                    keyword=rec["keyword"],
                    rank=rec.get("rank"),
                    heat_score=rec.get("heat_score"),
                    url=rec.get("url"),
                    collected_at=rec["collected_at"],
                )
            )
        total_records += len(records)

    await db.commit()

    # AI relevance scoring for newly collected keywords
    from app.config import settings as app_settings

    relevance_scores: dict[str, dict] = {}
    if app_settings.relevance_filter_enabled and total_records > 0:
        relevance_scores = await _score_new_keywords(db, hour_start, hour_end)

    # Detect trend signals (rank jumps, new entries, heat surges)
    from app.services.signals import auto_analyze_signals, detect_signals

    signals = await detect_signals(db)

    # Auto-analyze top signals with AI (if configured)
    from app.config import settings

    if signals and settings.signal_auto_analyze_limit > 0:
        await auto_analyze_signals(db, signals, limit=settings.signal_auto_analyze_limit)

    # Auto deep analysis on highest-scored keywords (Stage 3)
    if relevance_scores and settings.deep_analysis_auto_max > 0:
        from app.services.deep_analysis import auto_deep_analyze

        await auto_deep_analyze(db, relevance_scores)

    return {"status": "ok", "records_count": total_records, "platforms": platform_results}


# ---------------------------------------------------------------------------
# Streaming (SSE) variant — yields progress events as JSON dicts
# ---------------------------------------------------------------------------


async def run_all_collectors_stream(
    db: AsyncSession,
    platforms: list[str] | None = None,
):
    """Async generator that yields progress dicts for each pipeline stage.

    Each yielded dict has at least ``{"stage": ..., "message": ...}``.
    The final event has ``"stage": "done"``.
    """
    from app.services.platform_state import get_enabled_platforms

    if platforms is None:
        platforms = get_enabled_platforms()
    else:
        enabled = set(get_enabled_platforms())
        platforms = [p for p in platforms if p in enabled]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    # --- Stage: collecting (per-platform via queue workers) ---
    yield {"stage": "collecting", "message": f"开始采集 {len(platforms)} 个平台..."}

    in_q: asyncio.Queue[str] = asyncio.Queue()
    out_q: asyncio.Queue[_CollectResult] = asyncio.Queue()

    for slug in platforms:
        in_q.put_nowait(slug)

    workers = [
        asyncio.create_task(_queue_worker_stream(in_q, out_q)) for _ in range(_NUM_WORKERS)
    ]

    total_records = 0
    platform_results = []
    collected = 0

    while collected < len(platforms):
        platform_slug, records, error = await out_q.get()
        collected += 1
        platform_results.append({"platform": platform_slug, "count": len(records), "error": error})

        if error:
            yield {
                "stage": "collecting",
                "platform": platform_slug,
                "count": 0,
                "error": error,
                "message": f"{platform_slug} 采集失败: {error}",
            }
        else:
            yield {
                "stage": "collecting",
                "platform": platform_slug,
                "count": len(records),
                "message": f"{platform_slug} 采集完成 +{len(records)} 条",
            }

        if records:
            await db.execute(
                delete(Trend).where(
                    Trend.platform == platform_slug,
                    Trend.collected_at >= hour_start,
                    Trend.collected_at < hour_end,
                )
            )
            platform_id = await _ensure_platform(db, platform_slug)
            for rec in records:
                db.add(
                    Trend(
                        platform_id=platform_id,
                        platform=rec["platform"],
                        keyword=rec["keyword"],
                        rank=rec.get("rank"),
                        heat_score=rec.get("heat_score"),
                        url=rec.get("url"),
                        collected_at=rec["collected_at"],
                    )
                )
            total_records += len(records)

    for w in workers:
        w.cancel()

    await db.commit()
    yield {
        "stage": "collected",
        "records_count": total_records,
        "platforms": platform_results,
        "message": f"采集完成，共 {total_records} 条",
    }

    # --- Stage: scoring ---
    from app.config import settings as app_settings

    relevance_scores: dict[str, dict] = {}
    if app_settings.relevance_filter_enabled and total_records > 0:
        yield {"stage": "scoring", "message": "AI 相关性评分中..."}
        relevance_scores = await _score_new_keywords(db, hour_start, hour_end)
        relevant_count = sum(1 for v in relevance_scores.values() if v.get("label") == "relevant")
        yield {
            "stage": "scoring",
            "total": len(relevance_scores),
            "relevant": relevant_count,
            "message": f"评分完成: {relevant_count}/{len(relevance_scores)} 条相关",
        }

    # --- Stage: signals ---
    from app.services.signals import auto_analyze_signals, detect_signals

    yield {"stage": "signals", "message": "信号检测中..."}
    signals = await detect_signals(db)
    yield {
        "stage": "signals",
        "count": len(signals),
        "message": f"检测到 {len(signals)} 个信号",
    }

    from app.config import settings

    if signals and settings.signal_auto_analyze_limit > 0:
        yield {"stage": "signals", "message": "AI 分析信号中..."}
        analyzed = await auto_analyze_signals(db, signals, limit=settings.signal_auto_analyze_limit)
        yield {
            "stage": "signals",
            "analyzed": analyzed,
            "message": f"已分析 {analyzed} 个信号",
        }

    # --- Stage: deep_analysis ---
    if relevance_scores and settings.deep_analysis_auto_max > 0:
        from app.services.deep_analysis import auto_deep_analyze

        yield {"stage": "deep_analysis", "message": "深度分析中..."}
        deep_results = await auto_deep_analyze(db, relevance_scores)
        yield {
            "stage": "deep_analysis",
            "count": len(deep_results),
            "message": f"深度分析完成: {len(deep_results)} 个关键词",
        }

    # --- Done ---
    yield {
        "stage": "done",
        "records_count": total_records,
        "platforms": platform_results,
        "message": "全部完成",
    }
