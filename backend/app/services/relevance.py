"""AI-based trend relevance filter — scores keywords by personal relevance."""

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
    """Score a single batch of keywords.

    Uses a minimal output format: LLM returns only the indices of relevant
    keywords as a JSON array of numbers, e.g. ``[1, 3, 7]``.
    Everything not in the list is irrelevant.
    """
    numbered = "\n".join(f"{i + 1}. {kw}" for i, kw in enumerate(keywords))
    prompt = (
        "你是一个严格的信息过滤助手。\n\n"
        f"## 用户画像\n{user_profile}\n\n"
        "## 相关的条件（必须满足至少一项）\n"
        "- AI、大模型、芯片、半导体等科技\n"
        "- 电商、跨境贸易、直播带货、线上经济\n"
        "- 股市、基金、投资、金融\n"
        "- 加密货币、比特币、Web3\n"
        "- 创业、融资、商业模式、互联网产品\n"
        "- 影响上述领域的政策法规、经济数据\n\n"
        "## 不相关的（一律排除）\n"
        "明星八卦、综艺、影视剧、体育赛事、社会新闻、"
        "天气、灾害、情感婚恋、美食旅游\n\n"
        f"## 待判断的热搜关键词\n{numbered}\n\n"
        "请只返回相关条目的序号，用JSON数组格式。\n"
        "例如如果第1、3、7条相关，返回: [1,3,7]\n"
        "如果全部不相关，返回: []\n"
        "只返回JSON数组，不要任何其他文字。"
    )

    try:
        provider = LLMFactory.create()
        response = await provider.chat(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.1,
        )

        raw = response.content
        logger.warning("Relevance LLM raw response: %s", raw[:500])
        parsed = _parse_index_list(raw, keywords)
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


def _parse_index_list(content: str, keywords: list[str]) -> dict[str, dict]:
    """Parse LLM response as a list of relevant indices.

    Expected format: ``[1, 3, 7]`` — indices (1-based) of relevant keywords.
    All other keywords are marked irrelevant.
    """
    text = content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Extract all numbers from the text (handles messy formats like "[1, 3, 7]" or "1,3,7")
    numbers = set()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, (int, float)):
                    numbers.add(int(item))
    except json.JSONDecodeError:
        # Fallback: extract numbers with regex
        numbers = {int(m) for m in re.findall(r"\b(\d+)\b", text)}
        if numbers:
            logger.warning("Relevance: JSON parse failed, extracted numbers via regex: %s", numbers)
        else:
            logger.warning("Relevance: could not parse response: %s", text[:300])
            return {}

    # Build result: indices in the set are relevant, others are irrelevant
    result: dict[str, dict] = {}
    for i, kw in enumerate(keywords):
        idx = i + 1  # 1-based
        if idx in numbers:
            result[kw] = {"score": 80.0, "label": "relevant"}
        else:
            result[kw] = {"score": 10.0, "label": "irrelevant"}

    return result


# Keep old name for test imports
_parse_response = _parse_index_list
