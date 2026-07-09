import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger()

IMPORTANCE_THRESHOLD = 0.5

IMPORTANT_KEYWORDS = {
    "并购", "重组", "收购", "业绩", "预增", "预减", "亏损",
    "增持", "减持", "回购", "涨停", "跌停", "处罚", "退市",
    "合同", "中标", "专利", "股权激励", "分红",
}


@dataclass
class RawNews:
    """采集器输出的标准化原始资讯（内存临时对象，不直接落盘）"""
    source: str
    source_id: str
    title: str
    content: str | None = None
    url: str = ""
    published_at: datetime | None = None
    category: str = "news"
    extra: dict = field(default_factory=dict)


class BaseCollector(ABC):
    source: str = ""
    base_url: str = ""
    rate_limit: float = 1.0

    def __init__(self):
        self._seen_ids: set[str] = set()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
        return self._client

    async def collect(self, max_pages: int = 5) -> list[RawNews]:
        """采集入口：全量采集 → 去重 → 重要度过滤"""
        raw_items = []
        for page in range(1, max_pages + 1):
            try:
                items = await self.fetch_list(page)
                if not items:
                    break
                raw_items.extend(items)
            except Exception as e:
                logger.error("collect_page_failed", source=self.source, page=page, error=str(e))
                break

        deduped = self._deduplicate(raw_items)
        important = self._filter_important(deduped)
        logger.info("collect_done", source=self.source, raw=len(raw_items), deduped=len(deduped), important=len(important))
        return important

    def _deduplicate(self, items: list[RawNews]) -> list[RawNews]:
        seen: set[str] = set()
        result = []
        for item in items:
            key = f"{item.source}:{item.source_id}"
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        filtered = []
        for item in items:
            score = self._calc_importance(item)
            if score >= IMPORTANCE_THRESHOLD:
                item.extra["importance_score"] = score
                filtered.append(item)
        return filtered

    def _calc_importance(self, item: RawNews) -> float:
        score = 0.0
        title = item.title or ""

        # 涉及上市公司（标题中的代码 或 API自带的股票代码）
        has_stock = bool(re.search(r"[036]\d{5}", title)) or bool(item.extra.get("stock_codes"))
        if has_stock:
            score += 0.3

        # 重大事件关键词
        if any(kw in title for kw in IMPORTANT_KEYWORDS):
            score += 0.3

        # 来源权重
        source_weight = {"announcement": 0.2, "policy": 0.2, "news": 0.1, "social": 0.05}
        score += source_weight.get(item.category, 0.05)

        # 标题过短降权
        if len(title) < 10:
            score -= 0.1

        return min(max(score, 0.0), 1.0)

    @abstractmethod
    async def fetch_list(self, page: int) -> list[RawNews]:
        """获取资讯列表页"""

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
