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
    platform_count: int,
    age_hours: float,
    max_heat: float,
) -> float:
    """Compute a convergence score in the range [0, 100].

    Formula (weighted sum, then exponential recency decay):
    - heat_component  (50%): heat_score / max_heat * 100
    - rank_component  (30%): linear from rank 1 (100) to rank 50 (0)
    - platform_component (20%): each additional platform beyond the first adds score

    Recency decay: half-life of 12 hours — score halves every 12 hours of age.
    """
    # Heat component
    if heat_score and max_heat > 0:
        heat_component = min(100.0, heat_score / max_heat * 100)
    else:
        heat_component = 0.0

    # Rank component (rank is 0-based from Weibo; treat as 1-based for scoring)
    if rank is not None:
        effective_rank = rank + 1 if rank >= 0 else rank
        rank_component = max(0.0, (50 - effective_rank) / 50 * 100)
    else:
        rank_component = 0.0

    # Platform component: 0 extra platforms = 0, 4+ extra = 100
    platform_component = min(100.0, (platform_count - 1) / 4 * 100)

    raw = heat_component * 0.5 + rank_component * 0.3 + platform_component * 0.2

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

    # Global max heat for normalization
    max_result = await db.execute(select(func.max(Trend.heat_score)))
    max_heat = float(max_result.scalar_one() or 0.0)

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
            platform_count=1,  # per-row; cross-platform used in /top
            age_hours=age_hours,
            max_heat=max_heat,
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

    Aggregates by keyword across platforms, computes full convergence_score
    including cross-platform factor.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)

    result = await db.execute(
        select(Trend).where(Trend.collected_at >= since).order_by(Trend.collected_at.desc())
    )
    rows = result.scalars().all()

    # Global max heat for normalization
    max_heat = max((r.heat_score for r in rows if r.heat_score is not None), default=0.0)

    # Aggregate by keyword: collect platforms, best rank, max heat, latest time
    keyword_data: dict[str, dict] = {}
    for row in rows:
        kw = row.keyword
        if kw not in keyword_data:
            keyword_data[kw] = {
                "platforms": set(),
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
        latest = _to_naive_utc(row.collected_at)
        if latest > entry["latest"]:
            entry["latest"] = latest

    # Score each keyword
    scored = []
    for kw, entry in keyword_data.items():
        age_hours = max(0.0, (now - entry["latest"]).total_seconds() / 3600)
        score = compute_convergence_score(
            heat_score=entry["max_heat"],
            rank=entry["best_rank"],
            platform_count=len(entry["platforms"]),
            age_hours=age_hours,
            max_heat=max_heat,
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
