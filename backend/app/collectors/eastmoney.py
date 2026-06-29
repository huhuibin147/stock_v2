import json
import re
from datetime import datetime

import structlog

from app.collectors.base import BaseCollector, RawNews

logger = structlog.get_logger()

# 东方财富资讯API
NEWS_API = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
FLASH_API = "https://np-anotice-stock.eastmoney.com/api/security/ann"

# 栏目ID
COLUMN_IDS = "245,250"  # 要闻, 公司


class EastMoneyCollector(BaseCollector):
    source = "eastmoney"
    base_url = "https://www.eastmoney.com"
    rate_limit = 2.0

    async def fetch_list(self, page: int) -> list[RawNews]:
        items = []

        # 快讯/新闻
        news_items = await self._fetch_news(page)
        items.extend(news_items)

        return items

    async def _fetch_news(self, page: int) -> list[RawNews]:
        """采集东方财富新闻"""
        client = await self._get_client()
        items = []

        try:
            resp = await client.get(
                NEWS_API,
                params={
                    "client": "web",
                    "biz": "web_news_col",
                    "column": COLUMN_IDS,
                    "order": "1",
                    "needInteractData": "0",
                    "page_index": page,
                    "page_size": "50",
                },
            )
            data = resp.json()

            news_list = data.get("data", {}).get("list", [])
            for item in news_list:
                title = item.get("title", "").strip()
                if not title:
                    continue

                # 解析时间
                pub_time = None
                if item.get("showTime"):
                    try:
                        pub_time = datetime.strptime(item["showTime"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

                news_id = str(item.get("art_uniqueUrl", "").split("/")[-1].replace(".html", ""))
                if not news_id:
                    news_id = str(item.get("art_code", ""))

                items.append(RawNews(
                    source="eastmoney",
                    source_id=news_id or str(item.get("art_code", page * 100 + len(items))),
                    title=title,
                    content=item.get("content", ""),
                    url=item.get("art_uniqueUrl", ""),
                    published_at=pub_time,
                    category="news",
                ))

        except Exception as e:
            logger.error("eastmoney_fetch_failed", page=page, error=str(e))

        return items

    async def close(self):
        await super().close()
