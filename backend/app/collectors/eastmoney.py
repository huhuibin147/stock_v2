from datetime import datetime

import structlog

from app.collectors.base import BaseCollector, RawNews

logger = structlog.get_logger()

# 东方财富7x24快讯API（直接HTTP，不依赖akshare）
FAST_NEWS_API = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"

# fastColumn: 102=7x24快讯
# 用sortEnd翻页，pageSize控制每页数量


class EastMoneyCollector(BaseCollector):
    source = "eastmoney"
    base_url = "https://www.eastmoney.com"
    rate_limit = 1.5

    def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        """财经快讯全部保留，来源本身已是筛选过的"""
        for item in items:
            item.extra["importance_score"] = self._calc_importance(item)
        return items

    async def fetch_list(self, page: int) -> list[RawNews]:
        """采集7x24快讯"""
        client = await self._get_client()
        items = []

        try:
            params = {
                "client": "web",
                "biz": "web_724",
                "fastColumn": "102",
                "sortEnd": self._sort_end if hasattr(self, "_sort_end") and page > 1 else "",
                "pageSize": "50",
                "req_trace": str(int(datetime.now().timestamp() * 1000)),
            }

            resp = await client.get(FAST_NEWS_API, params=params)
            data = resp.json()

            if data.get("code") != "1":
                logger.warning("eastmoney_api_error", code=data.get("code"), msg=data.get("message"))
                return []

            news_list = data.get("data", {}).get("fastNewsList", [])
            self._sort_end = data.get("data", {}).get("sortEnd", "")

            for item in news_list:
                title = item.get("title", "").strip()
                summary = item.get("summary", "").strip()
                if not title:
                    continue

                # 解析时间
                pub_time = None
                show_time = item.get("showTime", "")
                if show_time:
                    try:
                        pub_time = datetime.strptime(show_time, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

                # 解析关联股票代码
                stock_codes = []
                for code in item.get("stockList", []):
                    if "." in code:
                        parts = code.split(".")
                        if len(parts) == 2:
                            market_id, symbol = parts
                            # 只保留A股: market 0=SZ, 1=SH
                            if market_id in ("0", "1") and symbol.isdigit() and len(symbol) == 6:
                                stock_codes.append(symbol)

                source_id = item.get("code", "")
                if not source_id:
                    continue

                items.append(RawNews(
                    source="eastmoney",
                    source_id=source_id,
                    title=title,
                    content=summary,
                    url=f"https://finance.eastmoney.com/a/{source_id}.html",
                    published_at=pub_time,
                    category="news",
                    extra={"stock_codes": stock_codes},
                ))

        except Exception as e:
            logger.error("eastmoney_fetch_failed", page=page, error=str(e))

        return items
