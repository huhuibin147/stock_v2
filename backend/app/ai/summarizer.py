import json

import structlog

from app.core.config import settings
from app.ai.prompts import SUMMARIZE_PROMPT

logger = structlog.get_logger()

_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.openai_api_key:
            return None
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _client


SENTIMENT_MAP = {"利好": 1, "利空": -1, "中性": 0}


async def summarize(title: str, content: str | None, source: str) -> dict:
    """生成资讯摘要。无API Key时降级为截取标题。"""
    client = _get_client()
    if not client:
        return _fallback_summary(title)

    content_section = f"内容：{content[:2000]}" if content else ""
    prompt = SUMMARIZE_PROMPT.format(title=title, source=source, content_section=content_section)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content
        # 提取JSON部分
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())
        return {
            "summary": result.get("summary", title[:50]),
            "key_points": result.get("key_points", []),
            "sentiment": SENTIMENT_MAP.get(result.get("sentiment", "中性"), 0),
            "impact_level": result.get("impact_level", "medium"),
        }
    except Exception as e:
        logger.error("summarize_failed", error=str(e), title=title[:50])
        return _fallback_summary(title)


def _fallback_summary(title: str) -> dict:
    """无API时的降级摘要"""
    return {
        "summary": title[:50],
        "key_points": [],
        "sentiment": 0,
        "impact_level": "medium",
    }
