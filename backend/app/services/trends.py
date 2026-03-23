"""Trends service — DB queries and convergence scoring for trend data."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend
from app.services.platform_state import get_enabled_platforms

# ---------------------------------------------------------------------------
# Simple counts
# ---------------------------------------------------------------------------


async def get_total_count(db: AsyncSession) -> int:
    """Return the total number of trend records in the database (all-time)."""
    result = await db.execute(select(func.count()).select_from(Trend))
    return result.scalar() or 0


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


async def get_trends(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    platform: str | None = None,
    relevant_only: bool = False,
) -> dict:
    """Return paginated trends sorted by convergence_score (per-platform normalised).

    When *platform* is provided, only records from that platform are returned.
    Uses a CTE to compute per-platform max heat_score within the last 24 hours so that
    heat normalisation is scoped to the same window as the displayed data — preventing
    stale all-time maximums from deflating scores.  Sorting and pagination are performed
    in Python because the recency-decay formula uses datetime arithmetic that is not
    portable across MySQL (production) and SQLite (tests).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)
    offset = (page - 1) * page_size

    enabled = get_enabled_platforms()
    base_filter = (Trend.collected_at >= since) & (Trend.platform.in_(enabled))
    if platform:
        base_filter = base_filter & (Trend.platform == platform)

    # CTE: per-platform max heat_score scoped to the last 24 h window.
    platform_max_cte = (
        select(
            Trend.platform.label("platform"),
            func.max(Trend.heat_score).label("max_heat"),
        )
        .where(base_filter)
        .group_by(Trend.platform)
        .cte("platform_max")
    )

    # Fetch all matching records with their platform's max_heat attached via the CTE.
    rows = (
        await db.execute(
            select(Trend, platform_max_cte.c.max_heat)
            .join(platform_max_cte, Trend.platform == platform_max_cte.c.platform)
            .where(base_filter)
        )
    ).all()

    # Score every record in Python (portable datetime arithmetic for recency decay).
    # Deduplicate by (platform, keyword): keep only the entry with the highest score.
    best: dict[tuple[str, str], tuple[Trend, float]] = {}
    for t, max_heat in rows:
        # When relevant_only is set, only keep items explicitly marked relevant
        if relevant_only and t.relevance_label != "relevant":
            continue
        age_hours = max(0.0, (now - _to_naive_utc(t.collected_at)).total_seconds() / 3600)
        score = compute_convergence_score(
            heat_score=t.heat_score,
            rank=t.rank,
            age_hours=age_hours,
            platform_max_heat=float(max_heat or 0.0),
        )
        key = (t.platform, t.keyword)
        if key not in best or score > best[key][1]:
            best[key] = (t, score)

    scored = list(best.values())

    # Sort by convergence_score descending, then paginate in Python.
    scored.sort(key=lambda x: x[1], reverse=True)
    total = len(scored)
    page_slice = scored[offset : offset + page_size]

    items = [
        {
            "platform": t.platform,
            "keyword": t.keyword,
            "rank": t.rank,
            "heat_score": t.heat_score,
            "url": t.url,
            "collected_at": t.collected_at,
            "convergence_score": score,
            "relevance_score": t.relevance_score,
            "relevance_label": t.relevance_label,
        }
        for t, score in page_slice
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_top_trends(
    db: AsyncSession, limit: int = 20, relevant_only: bool = False
) -> list[dict]:
    """Return top-N keywords by convergence_score over the last 24 hours.

    Aggregates by keyword (may span platforms), scores using per-platform max_heat.
    Cross-platform comparison is approximate — prefer /top-by-platform for display.
    When *relevant_only* is True, only keywords marked as "relevant" are included.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)
    enabled = get_enabled_platforms()

    stmt = select(Trend).where(Trend.collected_at >= since, Trend.platform.in_(enabled))
    if relevant_only:
        stmt = stmt.where(Trend.relevance_label == "relevant")
    result = await db.execute(stmt.order_by(Trend.collected_at.desc()))
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
    enabled = get_enabled_platforms()

    result = await db.execute(
        select(Trend)
        .where(Trend.collected_at >= since, Trend.platform.in_(enabled))
        .order_by(Trend.collected_at.desc())
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
    """Return enabled platform slugs."""
    return get_enabled_platforms()


# ---------------------------------------------------------------------------
# Velocity & Acceleration — trend momentum indicators
# ---------------------------------------------------------------------------


async def get_keyword_velocity(
    db: AsyncSession,
    platform: str | None = None,
    hours: int = 24,
    limit: int = 50,
) -> list[dict]:
    """Compute velocity (heat % change) and acceleration for each keyword.

    Divides the *hours* window into 3 equal periods (T0, T1, T2 = latest).
    - velocity = (heat_T2 - heat_T1) / max(heat_T1, 1) * 100  (% change)
    - acceleration = velocity_T2 - velocity_T1

    Returns list sorted by abs(velocity) descending, capped at *limit*.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period = timedelta(hours=hours / 3)
    t0_start = now - timedelta(hours=hours)
    t1_start = t0_start + period
    t2_start = t1_start + period

    enabled = get_enabled_platforms()
    base = select(
        Trend.platform,
        Trend.keyword,
        Trend.heat_score,
        Trend.rank,
        Trend.collected_at,
    ).where(Trend.collected_at >= t0_start, Trend.platform.in_(enabled))
    if platform:
        base = base.where(Trend.platform == platform)

    result = await db.execute(base)
    rows = result.all()

    # Bucket rows into 3 periods keyed by (platform, keyword)
    Key = tuple[str, str]
    buckets: dict[Key, dict[str, list]] = {}
    for plat, kw, heat, rank, collected in rows:
        key: Key = (plat, kw)
        if key not in buckets:
            buckets[key] = {"t0": [], "t1": [], "t2": []}
        collected_naive = _to_naive_utc(collected)
        if collected_naive < t1_start:
            buckets[key]["t0"].append((heat or 0.0, rank))
        elif collected_naive < t2_start:
            buckets[key]["t1"].append((heat or 0.0, rank))
        else:
            buckets[key]["t2"].append((heat or 0.0, rank))

    scored: list[dict] = []
    for (plat, kw), periods in buckets.items():
        avg_t0 = _avg_heat(periods["t0"])
        avg_t1 = _avg_heat(periods["t1"])
        avg_t2 = _avg_heat(periods["t2"])

        # Need at least T2 data to be meaningful
        if not periods["t2"]:
            continue

        vel_t1 = _pct_change(avg_t0, avg_t1)
        vel_t2 = _pct_change(avg_t1, avg_t2)

        accel = round(vel_t2 - vel_t1, 2) if vel_t1 is not None else None

        # Latest rank from T2
        latest_rank = periods["t2"][-1][1]

        scored.append(
            {
                "platform": plat,
                "keyword": kw,
                "heat_score": avg_t2,
                "rank": latest_rank,
                "velocity": vel_t2,
                "acceleration": accel,
            }
        )

    scored.sort(key=lambda x: abs(x["velocity"] or 0), reverse=True)
    return scored[:limit]


def _avg_heat(entries: list[tuple[float, int | None]]) -> float:
    """Average heat score from a list of (heat, rank) tuples."""
    if not entries:
        return 0.0
    return sum(h for h, _ in entries) / len(entries)


def _pct_change(old: float, new: float) -> float | None:
    """Percentage change from old to new. Returns None if old is 0."""
    if old <= 0:
        if new > 0:
            return 100.0  # appeared from nothing → cap at 100%
        return 0.0
    return round((new - old) / old * 100, 2)


async def get_heatmap(db: AsyncSession) -> dict:
    """Build heatmap data for the last 24 hours, grouped by platform × hour."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(hours=24)

    slots: list[datetime] = [
        (now - timedelta(hours=23 - i)).replace(minute=0, second=0, microsecond=0)
        for i in range(24)
    ]
    slot_index: dict[str, int] = {s.strftime("%Y-%m-%d %H"): i for i, s in enumerate(slots)}

    enabled = get_enabled_platforms()
    result = await db.execute(
        select(Trend.platform, Trend.collected_at, Trend.heat_score).where(
            Trend.collected_at >= since,
            Trend.platform.in_(enabled),
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
