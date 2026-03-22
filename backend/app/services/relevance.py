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
        "你是一个严格的信息过滤助手。你的任务是帮用户过滤掉无关信息。\n"
        "请严格按照用户画像判断，只有直接相关的才标 relevant，其余一律标 irrelevant。\n"
        "通常热搜中大部分（60-80%）是娱乐、社会新闻，应该被过滤掉。\n\n"
        f"## 用户画像\n{user_profile}\n\n"
        "## 标为 relevant 的条件（必须满足至少一项）\n"
        "- AI、大模型、芯片、半导体等科技领域\n"
        "- 电商、跨境贸易、直播带货、线上经济\n"
        "- 股市、基金、A股、美股、港股、投资\n"
        "- 加密货币、比特币、以太坊、Web3\n"
        "- 创业、融资、商业模式、互联网产品\n"
        "- 影响上述领域的政策法规、经济数据\n\n"
        "## 标为 irrelevant 的内容\n"
        "- 明星、演员、歌手、偶像、综艺、影视剧\n"
        "- 体育赛事、球星、运动员\n"
        "- 社会事件、交通事故、天气、自然灾害\n"
        "- 情感、家庭、婚恋、八卦\n"
        "- 美食、旅游、生活方式（除非涉及电商/创业）\n\n"
        f"## 待判断的热搜关键词\n{numbered}\n\n"
        "## 输出格式（必须紧凑，不要换行和空格）\n"
        "返回紧凑JSON数组，示例：\n"
        '[{"i":1,"l":"relevant","s":80},{"i":2,"l":"irrelevant","s":10}]\n'
        "字段：i=序号，l=label，s=score(0-100)\n"
        "只返回JSON，不要其他文字。"
    )

    try:
        provider = LLMFactory.create()
        response = await provider.chat(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.1,
        )

        logger.info("Relevance LLM response: %s", response.content[:500])
        parsed = _parse_response(response.content, keywords)
        logger.info(
            "Relevance result: %d/%d relevant",
            sum(1 for v in parsed.values() if v["label"] == "relevant"),
            len(parsed),
        )
        return parsed
    except Exception:
        logger.exception("Relevance scoring failed for batch of %d keywords", len(keywords))
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
        logger.warning("Failed to parse relevance response as JSON: %s", text[:300])
        return {}

    if not isinstance(items, list):
        logger.warning("Relevance response is not a list: %s", type(items))
        return {}

    result: dict[str, dict] = {}

    # Build index-based lookup for matching by index (more robust than keyword matching)
    kw_by_index = {i + 1: kw for i, kw in enumerate(keywords)}

    for item in items:
        # Support both compact ("i","l","s") and full ("index","label","score") keys
        idx = item.get("i") or item.get("index")
        kw_from_item = item.get("keyword", "")
        matched_kw = None

        if idx is not None and int(idx) in kw_by_index:
            matched_kw = kw_by_index[int(idx)]
        elif kw_from_item in keywords:
            matched_kw = kw_from_item
        else:
            for orig_kw in keywords:
                if orig_kw in kw_from_item or kw_from_item in orig_kw:
                    matched_kw = orig_kw
                    break

        if matched_kw is None:
            continue

        score = float(item.get("s") or item.get("score") or 50)
        label = item.get("l") or item.get("label") or ""
        if label not in ("relevant", "irrelevant"):
            label = "relevant" if score >= 50 else "irrelevant"
        result[matched_kw] = {"score": min(100.0, max(0.0, score)), "label": label}

    if len(result) < len(keywords):
        missed = [kw for kw in keywords if kw not in result]
        logger.warning(
            "Relevance parse: %d/%d matched, missed: %s",
            len(result),
            len(keywords),
            missed,
        )

    return result
