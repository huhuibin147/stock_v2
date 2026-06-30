from datetime import datetime

import structlog

from app.collectors.base import BaseCollector, RawNews

logger = structlog.get_logger()

# 新浪财经滚动新闻API
SINA_ROLL_API = "https://feed.mix.sina.com.cn/api/roll/get"

# lid=2516 财经要闻, lid=2517 公司新闻, lid=2669 全部


class SinaCollector(BaseCollector):
    source = "sina"
    base_url = "https://finance.sina.com.cn"
    rate_limit = 1.5

    def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        """财经资讯全部保留"""
        for item in items:
            item.extra["importance_score"] = self._calc_importance(item)
        return items
    rate_limit = 1.5

    def __init__(self):
        super().__init__()
        self._page_size = 50

    async def fetch_list(self, page: int) -> list[RawNews]:
        """采集新浪财经要闻"""
        client = await self._get_client()
        items = []

        try:
            params = {
                "pageid": "153",
                "lid": "2516",
                "k": "",
                "num": str(self._page_size),
                "page": str(page),
            }

            resp = await client.get(SINA_ROLL_API, params=params)
            data = resp.json()

            result = data.get("result", {})
            if result.get("status", {}).get("code") != 0:
                logger.warning("sina_api_error", status=result.get("status"))
                return []

            news_list = result.get("data", [])

            for item in news_list:
                title = item.get("title", "").strip()
                summary = item.get("summary", "").strip()
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

                # 关键词
                keywords_str = item.get("keywords", "")
                keywords = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str else []

                source_id = item.get("docid", "") or item.get("commentid", "")
                if not source_id:
                    continue

                items.append(RawNews(
                    source="sina",
                    source_id=source_id,
                    title=title,
                    content=summary,
                    url=item.get("url", ""),
                    published_at=pub_time,
                    category="news",
                    extra={
                        "media": item.get("media_name", ""),
                        "keywords": keywords,
                    },
                ))

        except Exception as e:
            logger.error("sina_fetch_failed", page=page, error=str(e))

        return items
