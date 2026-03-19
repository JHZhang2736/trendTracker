"""Trends service — DB queries and convergence scoring for trend data."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.registry import registry
from app.models.trend import Trend

# ---------------------------------------------------------------------------
# Convergence score — pure function, no I/O
# ---------------------------------------------------------------------------


def compute_convergence_score(
    heat_score: float | None,
    rank: int | None,
    age_hours: float,
    platform_max_heat: float,
) -> float:
    """Compute a convergence score in the range [0, 100].

    Formula (weighted sum, then exponential recency decay):
    - heat_component (50%): heat_score / platform_max_heat * 100  (same-platform normalization)
    - rank_component (50%): linear from rank 1 (100) to rank 50 (0)

    Scores are only meaningful within the same platform — cross-platform comparison
    is avoided because heat magnitude differs by orders of magnitude.

    Recency decay: half-life of 12 hours — score halves every 12 hours of age.
    """
    # Heat component: normalized within the same platform batch
    if heat_score and platform_max_heat > 0:
        heat_component = min(100.0, heat_score / platform_max_heat * 100)
    else:
        heat_component = 0.0

    # Rank component (rank is 0-based; treat as 1-based for scoring)
    if rank is not None:
        effective_rank = rank + 1 if rank >= 0 else rank
        rank_component = max(0.0, (50 - effective_rank) / 50 * 100)
    else:
        rank_component = 0.0

    raw = heat_component * 0.5 + rank_component * 0.5

    # Recency decay: half-life 12h
    decay = math.exp(-age_hours * math.log(2) / 12)

    return round(min(100.0, max(0.0, raw * decay)), 2)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _to_naive_utc(dt: datetime) -> datetime:
    """Strip timezone info from a datetime (DB stores naive UTC)."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def get_trends(db: AsyncSession, page: int = 1, page_size: int = 20) -> dict:
    """Return paginated trends with convergence_score, ordered by collected_at desc."""
    offset = (page - 1) * page_size
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    count_result = await db.execute(select(func.count()).select_from(Trend))
    total = count_result.scalar_one()

    # Per-platform max heat for normalization (avoids cross-platform magnitude bias)
    max_heat_rows = await db.execute(
        select(Trend.platform, func.max(Trend.heat_score)).group_by(Trend.platform)
    )
    platform_max_heat: dict[str, float] = {
        row.platform: float(row[1] or 0.0) for row in max_heat_rows
    }

    result = await db.execute(
        select(Trend)
        .order_by(Trend.collected_at.desc(), Trend.rank)
        .offset(offset)
        .limit(page_size)
    )
    trends = result.scalars().all()

    items = []
    for t in trends:
        collected = _to_naive_utc(t.collected_at)
        age_hours = max(0.0, (now - collected).total_seconds() / 3600)
        score = compute_convergence_score(
            heat_score=t.heat_score,
            rank=t.rank,
            age_hours=age_hours,
            platform_max_heat=platform_max_heat.get(t.platform, 0.0),
        )
        items.append(
            {
                "platform": t.platform,
                "keyword": t.keyword,
                "rank": t.rank,
                "heat_score": t.heat_score,
                "url": t.url,
                "collected_at": t.collected_at,
                "convergence_score": score,
            }
        )
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_top_trends(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Return top-N keywords by convergence_score over the last 24 hours.

    Aggregates by keyword (may span platforms), scores using per-platform max_heat.
    Cross-platform comparison is approximate — prefer /top-by-platform for display.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)

    result = await db.execute(
        select(Trend).where(Trend.collected_at >= since).order_by(Trend.collected_at.desc())
    )
    rows = result.scalars().all()

    # Per-platform max heat for normalization
    platform_max: dict[str, float] = {}
    for row in rows:
        if row.heat_score is not None:
            if row.platform not in platform_max or row.heat_score > platform_max[row.platform]:
                platform_max[row.platform] = row.heat_score

    # Aggregate by keyword: collect platforms, best rank, max heat, latest time
    keyword_data: dict[str, dict] = {}
    for row in rows:
        kw = row.keyword
        if kw not in keyword_data:
            keyword_data[kw] = {
                "platforms": set(),
                "best_platform": row.platform,
                "best_rank": row.rank,
                "max_heat": row.heat_score or 0.0,
                "latest": _to_naive_utc(row.collected_at),
                "url": row.url,
            }
        entry = keyword_data[kw]
        entry["platforms"].add(row.platform)
        if row.rank is not None and (entry["best_rank"] is None or row.rank < entry["best_rank"]):
            entry["best_rank"] = row.rank
        if row.heat_score and row.heat_score > entry["max_heat"]:
            entry["max_heat"] = row.heat_score
            entry["best_platform"] = row.platform
        latest = _to_naive_utc(row.collected_at)
        if latest > entry["latest"]:
            entry["latest"] = latest

    # Score each keyword using the platform that contributed the max heat
    scored = []
    for kw, entry in keyword_data.items():
        age_hours = max(0.0, (now - entry["latest"]).total_seconds() / 3600)
        p_max = platform_max.get(entry["best_platform"], 0.0)
        score = compute_convergence_score(
            heat_score=entry["max_heat"],
            rank=entry["best_rank"],
            age_hours=age_hours,
            platform_max_heat=p_max,
        )
        scored.append(
            {
                "keyword": kw,
                "platforms": sorted(entry["platforms"]),
                "max_heat_score": entry["max_heat"],
                "latest_collected_at": entry["latest"],
                "convergence_score": score,
            }
        )

    scored.sort(key=lambda x: x["convergence_score"], reverse=True)
    return scored[:limit]


async def get_top_trends_by_platform(db: AsyncSession, limit: int = 10) -> dict[str, list[dict]]:
    """Return top-N keywords per platform, each scored with per-platform normalization."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)

    result = await db.execute(
        select(Trend).where(Trend.collected_at >= since).order_by(Trend.collected_at.desc())
    )
    rows = result.scalars().all()

    # Group rows by platform
    platform_rows: dict[str, list] = {}
    for row in rows:
        platform_rows.setdefault(row.platform, []).append(row)

    output: dict[str, list[dict]] = {}
    for platform, prows in platform_rows.items():
        # Per-platform max heat
        platform_max = max((r.heat_score for r in prows if r.heat_score is not None), default=0.0)

        # Score each row; deduplicate keyword by best score
        keyword_best: dict[str, dict] = {}
        for row in prows:
            collected = _to_naive_utc(row.collected_at)
            age_hours = max(0.0, (now - collected).total_seconds() / 3600)
            score = compute_convergence_score(
                heat_score=row.heat_score,
                rank=row.rank,
                age_hours=age_hours,
                platform_max_heat=platform_max,
            )
            kw = row.keyword
            if kw not in keyword_best or score > keyword_best[kw]["convergence_score"]:
                keyword_best[kw] = {
                    "keyword": kw,
                    "rank": row.rank,
                    "heat_score": row.heat_score,
                    "url": row.url,
                    "collected_at": row.collected_at,
                    "convergence_score": score,
                }

        top = sorted(keyword_best.values(), key=lambda x: x["convergence_score"], reverse=True)[
            :limit
        ]
        output[platform] = top

    return output


def get_platforms() -> list[str]:
    """Return all registered platform slugs."""
    return registry.list_platforms()


async def get_heatmap(db: AsyncSession) -> dict:
    """Build heatmap data for the last 24 hours, grouped by platform × hour."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)

    slots: list[datetime] = [
        (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        for i in range(24)
    ]
    slot_index: dict[str, int] = {s.strftime("%Y-%m-%d %H"): i for i, s in enumerate(slots)}

    result = await db.execute(
        select(Trend.platform, Trend.collected_at, Trend.heat_score).where(
            Trend.collected_at >= since
        )
    )
    rows = result.all()

    platforms = sorted({row.platform for row in rows if row.platform})
    platform_index = {p: i for i, p in enumerate(platforms)}

    cells: dict[tuple[int, int], float] = {}
    for row in rows:
        if row.heat_score is None:
            continue
        p_idx = platform_index.get(row.platform)
        if p_idx is None:
            continue
        collected = _to_naive_utc(row.collected_at)
        hour_key = collected.strftime("%Y-%m-%d %H")
        s_idx = slot_index.get(hour_key)
        if s_idx is None:
            continue
        key = (p_idx, s_idx)
        cells[key] = max(cells.get(key, 0.0), float(row.heat_score))

    data = [[float(p), float(s), v] for (p, s), v in cells.items()]
    max_heat = max(cells.values(), default=0.0)
    time_labels = [s.strftime("%H:%M") for s in slots]

    return {
        "platforms": platforms,
        "time_slots": time_labels,
        "data": data,
        "max_heat": max_heat,
    }
