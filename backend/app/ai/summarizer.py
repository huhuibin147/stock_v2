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
    """生成资讯摘要。直接使用标题作为摘要，不调用AI API。"""
    return _fallback_summary(title)


def _fallback_summary(title: str) -> dict:
    """无API时的降级摘要"""
    return {
        "summary": title[:50],
        "key_points": [],
        "sentiment": 0,
        "impact_level": "medium",
    }
