"""AI-based trend relevance filter — scores keywords by personal relevance.

Stage 1 of the AI pipeline: filter irrelevant items AND score importance
in a single LLM call.
"""

from __future__ import annotations

import json
import logging
import re

from app.ai.base import ChatMessage
from app.ai.factory import LLMFactory

logger = logging.getLogger(__name__)

# Maximum keywords per LLM call to stay within token limits
_BATCH_SIZE = 30


async def score_relevance(
    keywords: list[str],
    user_profile: str,
) -> dict[str, dict]:
    """Score a list of keywords for personal relevance using LLM.

    Returns a dict keyed by keyword with ``score`` (0-100), ``label``
    ("relevant" | "irrelevant"), and ``reason`` (one-line explanation).
    """
    if not keywords:
        return {}

    results: dict[str, dict] = {}
    for i in range(0, len(keywords), _BATCH_SIZE):
        batch = keywords[i : i + _BATCH_SIZE]
        batch_result = await _score_batch(batch, user_profile)
        results.update(batch_result)

    return results


async def _score_batch(
    keywords: list[str],
    user_profile: str,
) -> dict[str, dict]:
    """Score a single batch of keywords.

    LLM returns a JSON array of objects with short keys:
    ``[{"i": 1, "s": 85, "r": "理由"}, ...]``
    - i: 1-based index of relevant keyword
    - s: importance score 0-100
    - r: one-line reason why it's relevant

    Keywords not in the list are irrelevant (score=0).
    """
    numbered = "\n".join(f"{i + 1}. {kw}" for i, kw in enumerate(keywords))
    prompt = (
        f"用户画像：{user_profile}\n\n"
        "对以下热搜逐条判断：这个用户能否从中找到商业行动机会？\n"
        "高分标准（60-100）：能直接做产品、卖货、做内容、投资决策\n"
        "中分标准（30-59）：行业趋势，间接启发商业思路\n"
        "过滤掉：无法转化为任何商业行动的纯新闻/八卦/事故\n\n"
        f"{numbered}\n\n"
        "逐条判断，有商业行动价值的给分数0-100和一句话行动启发（20字内）。\n"
        '格式：[{"i":序号,"s":分数,"r":"行动启发"},...] 只含有价值条目。全无价值返回[]'
    )

    try:
        provider = LLMFactory.create()
        response = await provider.chat(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.1,
        )

        raw = response.content
        logger.warning("Relevance LLM raw response: %s", raw[:500])
        parsed = _parse_scored_response(raw, keywords)
        relevant_count = sum(1 for v in parsed.values() if v["label"] == "relevant")
        logger.warning(
            "Relevance result: %d relevant, %d irrelevant out of %d",
            relevant_count,
            len(parsed) - relevant_count,
            len(parsed),
        )
        return parsed
    except Exception:
        logger.exception("Relevance scoring failed for batch of %d keywords", len(keywords))
        return {}


def _parse_scored_response(content: str, keywords: list[str]) -> dict[str, dict]:
    """Parse LLM response with scores and reasons.

    Expected format: ``[{"i": 1, "s": 85, "r": "理由"}, ...]``
    Falls back through multiple strategies if parsing fails.
    """
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Strategy 1: Parse full JSON with i/s/r objects
    scored_items = _try_parse_scored_json(text)

    if scored_items is not None:
        return _build_result_from_scored(scored_items, keywords)

    # Strategy 2: Regex extraction of i/s pairs from malformed JSON
    scored_items = _try_regex_scored(text)
    if scored_items:
        logger.warning("Relevance: JSON parse failed, used regex fallback")
        return _build_result_from_scored(scored_items, keywords)

    # Strategy 3: Fall back to pure index list [1, 3, 7] (no scores)
    numbers = _try_parse_index_list(text)
    if numbers is not None:
        logger.warning("Relevance: fell back to index-only mode (no scores)")
        result: dict[str, dict] = {}
        for i, kw in enumerate(keywords):
            idx = i + 1
            if idx in numbers:
                result[kw] = {"score": 80.0, "label": "relevant", "reason": ""}
            else:
                result[kw] = {"score": 0.0, "label": "irrelevant", "reason": ""}
        return result

    # Strategy 4: Complete failure
    logger.warning("Relevance: could not parse response: %s", text[:300])
    return {}


def _try_parse_scored_json(text: str) -> list[dict] | None:
    """Try to parse as JSON array of {i, s, r} objects."""
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            return None
        # Validate structure
        items = []
        for obj in parsed:
            if isinstance(obj, dict) and "i" in obj:
                items.append(
                    {
                        "i": int(obj["i"]),
                        "s": float(obj.get("s", 80)),
                        "r": str(obj.get("r", "")),
                    }
                )
            elif isinstance(obj, (int, float)):
                # Pure index list like [1, 3, 7] — treat as scored with default
                items.append({"i": int(obj), "s": 80.0, "r": ""})
        return items if items or parsed == [] else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _try_regex_scored(text: str) -> list[dict]:
    """Extract i/s pairs using regex from malformed JSON."""
    # Match patterns like "i":1,"s":85 or "i": 1, "s": 85
    pattern = r'"i"\s*:\s*(\d+)\s*,\s*"s"\s*:\s*(\d+)'
    matches = re.findall(pattern, text)
    if not matches:
        return []

    # Also try to extract reasons
    reason_pattern = r'"i"\s*:\s*(\d+)\s*,\s*"s"\s*:\s*(\d+)\s*,\s*"r"\s*:\s*"([^"]*)"'
    reason_matches = re.findall(reason_pattern, text)
    reason_map = {int(m[0]): m[2] for m in reason_matches}

    items = []
    for idx_str, score_str in matches:
        idx = int(idx_str)
        items.append(
            {
                "i": idx,
                "s": float(score_str),
                "r": reason_map.get(idx, ""),
            }
        )
    return items


def _try_parse_index_list(text: str) -> set[int] | None:
    """Try to parse as a simple list of numbers."""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(x, (int, float)) for x in parsed):
            return {int(x) for x in parsed}
    except json.JSONDecodeError:
        pass

    # Regex fallback
    numbers = {int(m) for m in re.findall(r"\b(\d+)\b", text)}
    return numbers if numbers else None


def _build_result_from_scored(scored_items: list[dict], keywords: list[str]) -> dict[str, dict]:
    """Build result dict from scored items list."""
    # Map index → {s, r}
    score_map: dict[int, dict] = {}
    for item in scored_items:
        score_map[item["i"]] = {"s": item["s"], "r": item["r"]}

    result: dict[str, dict] = {}
    for i, kw in enumerate(keywords):
        idx = i + 1
        info = score_map.get(idx)
        if info:
            score = max(0.0, min(100.0, info["s"]))
            result[kw] = {"score": score, "label": "relevant", "reason": info["r"]}
        else:
            result[kw] = {"score": 0.0, "label": "irrelevant", "reason": ""}

    return result


# Keep old name for backward compatibility
_parse_index_list = _try_parse_index_list
_parse_response = _parse_scored_response
