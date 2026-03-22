"""AI-based trend relevance filter — scores keywords by personal relevance."""

from __future__ import annotations

import json
import logging

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

    Returns a dict keyed by keyword with ``score`` (0-100) and ``label``
    ("relevant" | "irrelevant") for each keyword.
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
    """Score a single batch of keywords."""
    numbered = "\n".join(f"{i + 1}. {kw}" for i, kw in enumerate(keywords))
    prompt = (
        "你是一个信息过滤助手。根据用户画像，判断以下热搜关键词对该用户是否有参考价值。\n\n"
        f"## 用户画像\n{user_profile}\n\n"
        "## 判断标准\n"
        "- 与用户关注领域（AI科技、电商、线上经济、股市、加密货币、创业）相关 → relevant\n"
        "- 涉及政策法规、经济走势、行业变革等可能影响商业决策的 → relevant\n"
        "- 纯娱乐八卦、明星绯闻、综艺节目、体育赛事、社会新闻等 → irrelevant\n\n"
        f"## 热搜关键词\n{numbered}\n\n"
        "## 输出要求\n"
        "返回 JSON 数组，每项包含:\n"
        '- keyword: 原始关键词\n- score: 相关性评分 0-100\n- label: "relevant" 或 "irrelevant"\n\n'
        "只返回 JSON 数组，不要其他内容。"
    )

    try:
        provider = LLMFactory.create()
        response = await provider.chat(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.1,
        )

        parsed = _parse_response(response.content, keywords)
        return parsed
    except Exception:
        logger.exception("Relevance scoring failed for batch of %d keywords", len(keywords))
        # On failure, return empty — leave items unscored (no label assigned)
        return {}


def _parse_response(content: str, keywords: list[str]) -> dict[str, dict]:
    """Parse LLM JSON response into keyword → {score, label} dict."""
    # Strip markdown code fences if present
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse relevance response as JSON, leaving unscored")
        return {}

    result: dict[str, dict] = {}
    if isinstance(items, list):
        for item in items:
            kw = item.get("keyword", "")
            score = float(item.get("score", 50))
            label = item.get("label", "relevant")
            if label not in ("relevant", "irrelevant"):
                label = "relevant" if score >= 50 else "irrelevant"
            result[kw] = {"score": min(100.0, max(0.0, score)), "label": label}

    # Keywords not in the LLM response are left unscored (no entry)
    return result
