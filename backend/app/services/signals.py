"""Signal detection service — detect noteworthy trend signals after each collection.

Three signal types:
1. rank_jump   — keyword rank improved by ≥ 20 positions within 6 hours
2. new_entry   — keyword appears in Top 50 for the first time in 24 hours
3. heat_surge  — keyword heat_score is ≥ 2× the previous collection's value
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal_log import SignalLog
from app.models.trend import Trend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANK_JUMP_THRESHOLD = 20  # minimum rank improvement to trigger
RANK_JUMP_LOOKBACK_HOURS = 6
NEW_ENTRY_LOOKBACK_HOURS = 24
HEAT_SURGE_MULTIPLIER = 2.0
TOP_N = 50  # only consider trends ranked within Top N


# ---------------------------------------------------------------------------
# Core detection
# ---------------------------------------------------------------------------


async def detect_signals(db: AsyncSession) -> list[SignalLog]:
    """Run all signal detectors on fresh data. Returns list of new SignalLog rows."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    signals: list[SignalLog] = []

    signals.extend(await _detect_rank_jumps(db, now))
    signals.extend(await _detect_new_entries(db, now))
    signals.extend(await _detect_heat_surges(db, now))

    if signals:
        # Deduplicate: remove existing signals for the same keyword+platform+type
        # within the last hour to prevent spamming on repeated collections
        hour_ago = now - timedelta(hours=1)
        for sig in signals:
            await db.execute(
                delete(SignalLog).where(
                    SignalLog.signal_type == sig.signal_type,
                    SignalLog.platform == sig.platform,
                    SignalLog.keyword == sig.keyword,
                    SignalLog.detected_at >= hour_ago,
                )
            )
        db.add_all(signals)
        await db.commit()
        logger.info("detect_signals: %d signals detected", len(signals))
    else:
        logger.debug("detect_signals: no signals detected")

    return signals


# ---------------------------------------------------------------------------
# Signal 1: Rank Jump
# ---------------------------------------------------------------------------


async def _detect_rank_jumps(db: AsyncSession, now: datetime) -> list[SignalLog]:
    """Detect keywords whose rank improved by ≥ RANK_JUMP_THRESHOLD in 6h."""
    lookback = now - timedelta(hours=RANK_JUMP_LOOKBACK_HOURS)

    # Get latest trends (within the last hour) that have a rank
    latest_hour = now - timedelta(hours=1)
    result = await db.execute(
        select(Trend).where(
            Trend.collected_at >= latest_hour,
            Trend.rank.isnot(None),
            Trend.rank < TOP_N,
        )
    )
    current_trends = result.scalars().all()

    signals: list[SignalLog] = []
    for trend in current_trends:
        # Find the worst (highest number) rank for this keyword+platform in lookback
        old_rank_result = await db.execute(
            select(func.max(Trend.rank)).where(
                Trend.keyword == trend.keyword,
                Trend.platform == trend.platform,
                Trend.collected_at >= lookback,
                Trend.collected_at < latest_hour,
                Trend.rank.isnot(None),
            )
        )
        old_rank = old_rank_result.scalar()
        if old_rank is None:
            continue

        jump = old_rank - (trend.rank or 0)
        if jump >= RANK_JUMP_THRESHOLD:
            signals.append(
                SignalLog(
                    signal_type="rank_jump",
                    platform=trend.platform,
                    keyword=trend.keyword,
                    description=f"排名跃升: {old_rank} → {trend.rank} (↑{jump}位)",
                    value=float(jump),
                    detected_at=now,
                )
            )

    return signals


# ---------------------------------------------------------------------------
# Signal 2: New Entry
# ---------------------------------------------------------------------------


async def _detect_new_entries(db: AsyncSession, now: datetime) -> list[SignalLog]:
    """Detect keywords that appear in Top 50 for the first time in 24h."""
    latest_hour = now - timedelta(hours=1)
    lookback_24h = now - timedelta(hours=NEW_ENTRY_LOOKBACK_HOURS)

    # Get keywords from the latest collection
    result = await db.execute(
        select(Trend.keyword, Trend.platform, Trend.rank).where(
            Trend.collected_at >= latest_hour,
            Trend.rank.isnot(None),
            Trend.rank < TOP_N,
        )
    )
    current_entries = result.all()

    signals: list[SignalLog] = []
    for keyword, platform, rank in current_entries:
        # Check if this keyword+platform existed in the previous 24h (excluding latest hour)
        old_result = await db.execute(
            select(func.count()).where(
                Trend.keyword == keyword,
                Trend.platform == platform,
                Trend.collected_at >= lookback_24h,
                Trend.collected_at < latest_hour,
            )
        )
        old_count = old_result.scalar() or 0
        if old_count == 0:
            signals.append(
                SignalLog(
                    signal_type="new_entry",
                    platform=platform,
                    keyword=keyword,
                    description=f"新面孔: 首次进入 Top {TOP_N}, 当前排名 #{rank}",
                    value=float(rank) if rank is not None else None,
                    detected_at=now,
                )
            )

    return signals


# ---------------------------------------------------------------------------
# Signal 3: Heat Surge
# ---------------------------------------------------------------------------


async def _detect_heat_surges(db: AsyncSession, now: datetime) -> list[SignalLog]:
    """Detect keywords whose heat_score is ≥ 2× the previous collection."""
    latest_hour = now - timedelta(hours=1)

    # Get latest trends with heat_score
    result = await db.execute(
        select(Trend).where(
            Trend.collected_at >= latest_hour,
            Trend.heat_score.isnot(None),
            Trend.heat_score > 0,
        )
    )
    current_trends = result.scalars().all()

    signals: list[SignalLog] = []
    for trend in current_trends:
        # Find the most recent previous heat_score for this keyword+platform
        prev_result = await db.execute(
            select(Trend.heat_score)
            .where(
                Trend.keyword == trend.keyword,
                Trend.platform == trend.platform,
                Trend.collected_at < latest_hour,
                Trend.heat_score.isnot(None),
                Trend.heat_score > 0,
            )
            .order_by(Trend.collected_at.desc())
            .limit(1)
        )
        prev_heat = prev_result.scalar()
        if prev_heat is None or prev_heat <= 0:
            continue

        ratio = trend.heat_score / prev_heat
        if ratio >= HEAT_SURGE_MULTIPLIER:
            signals.append(
                SignalLog(
                    signal_type="heat_surge",
                    platform=trend.platform,
                    keyword=trend.keyword,
                    description=(
                        f"热度突增: {prev_heat:,.0f} → {trend.heat_score:,.0f}" f" ({ratio:.1f}x)"
                    ),
                    value=round(ratio, 2),
                    detected_at=now,
                )
            )

    return signals


# ---------------------------------------------------------------------------
# Query helpers (for router)
# ---------------------------------------------------------------------------


async def get_recent_signals(db: AsyncSession, hours: int = 24, limit: int = 50) -> list[SignalLog]:
    """Return most recent signals within the given time window."""
    from app.services.platform_state import get_enabled_platforms

    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours)
    enabled = get_enabled_platforms()
    result = await db.execute(
        select(SignalLog)
        .where(SignalLog.detected_at >= since, SignalLog.platform.in_(enabled))
        .order_by(SignalLog.detected_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Auto-analyze: AI-driven signal analysis
# ---------------------------------------------------------------------------


async def auto_analyze_signals(db: AsyncSession, signals: list[SignalLog], limit: int = 3) -> int:
    """Automatically run AI analysis on the top-N signals by value.

    Updates the ``ai_summary`` field on each analyzed SignalLog.
    Returns the number of signals analyzed.
    """
    if not signals or limit <= 0:
        return 0

    # Sort by value descending (biggest jump / surge first), take top N
    ranked = sorted(signals, key=lambda s: s.value or 0, reverse=True)[:limit]

    analyzed = 0
    for sig in ranked:
        try:
            from app.ai.base import ChatMessage
            from app.ai.factory import LLMFactory

            provider = LLMFactory.create()
            resp = await provider.chat(
                [
                    ChatMessage(
                        role="system",
                        content="你是商业趋势分析专家。用一句话概括这个热词的商业意义，50字以内。",
                    ),
                    ChatMessage(role="user", content=f"热词：{sig.keyword}"),
                ]
            )
            sig.ai_summary = resp.content[:500] if resp.content else None
            analyzed += 1
            logger.info("auto_analyze_signals: analyzed %r (%s)", sig.keyword, sig.signal_type)
        except Exception as exc:  # noqa: BLE001
            logger.warning("auto_analyze_signals: failed for %r — %s", sig.keyword, exc)

    if analyzed:
        await db.commit()

    return analyzed
