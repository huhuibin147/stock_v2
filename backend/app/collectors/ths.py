from datetime import datetime

import structlog

from app.collectors.base import BaseCollector, RawNews

logger = structlog.get_logger()

# 同花顺资讯API
THS_NEWS_API = "https://news.10jqka.com.cn/tapp/news/push/stock/"


class THSCollector(BaseCollector):
    source = "ths"
    base_url = "https://news.10jqka.com.cn"
    rate_limit = 2.0

    def __init__(self):
        super().__init__()
        self._page = 0

    async def fetch_list(self, page: int) -> list[RawNews]:
        """采集同花顺资讯"""
        client = await self._get_client()
        items = []

        try:
            # 同花顺用page参数翻页
            url = THS_NEWS_API
            if page > 1:
                url = f"{THS_NEWS_API}?page={page}"

            resp = await client.get(url)
            data = resp.json()

            if data.get("code") != "200":
                logger.warning("ths_api_error", code=data.get("code"), msg=data.get("msg"))
                return []

            news_list = data.get("data", {}).get("list", [])

            for item in news_list:
                title = item.get("title", "").strip()
                digest = item.get("digest", "").strip()
                if not title:
                    continue

                # 解析时间
                pub_time = None
                ctime = item.get("ctime", "")
                if ctime:
                    try:
                        pub_time = datetime.fromtimestamp(int(ctime))
                    except (ValueError, TypeError):
                        pass

                # 解析关联股票
                stock_codes = []
                for stock in item.get("stock", []):
                    code = stock.get("stockCode", "")
                    market_id = stock.get("stockMarket", "")
                    # 只保留A股: market 17=SH, 33=SZ
                    if market_id in ("17", "33") and code.isdigit() and len(code) == 6:
                        stock_codes.append(code)

                # 标签
                tags = [t.get("name", "") for t in item.get("tags", []) if t.get("name")]

                source_id = item.get("id", "")
                if not source_id:
                    continue

                items.append(RawNews(
                    source="ths",
                    source_id=source_id,
                    title=title,
                    content=digest,
                    url=item.get("url", ""),
                    published_at=pub_time,
                    category="news",
                    extra={"stock_codes": stock_codes, "tags": tags},
                ))

        except Exception as e:
            logger.error("ths_fetch_failed", page=page, error=str(e))

        return items
