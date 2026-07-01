from datetime import datetime, timedelta

import structlog

from app.collectors.base import BaseCollector, RawNews

logger = structlog.get_logger()


class CninfoCollector(BaseCollector):
    """巨潮资讯公告采集器（使用 AKShare stock_notice_report）"""

    source = "cninfo"
    base_url = "https://data.eastmoney.com/notices/hsa/5.html"
    rate_limit = 2.0

    # 只采集这些重要公告类型（其他如股东大会决议、分配方案等忽略）
    IMPORTANT_NOTICE_TYPES = {
        "重大事项",
        "资产重组",
        "风险提示",
        "持股变动",
        "融资公告",
        "财务报告",
        "信息变更",
        "处罚整改",
        "业绩预告",
        "业绩快报",
        "停牌公告",
        "退市",
    }

    # 公告类型 → 重要度加权
    NOTICE_WEIGHT = {
        "重大事项": 0.25,
        "资产重组": 0.25,
        "风险提示": 0.2,
        "持股变动": 0.2,
        "业绩预告": 0.2,
        "业绩快报": 0.2,
        "退市": 0.25,
        "处罚整改": 0.2,
        "停牌公告": 0.15,
        "融资公告": 0.1,
        "财务报告": 0.1,
        "信息变更": 0.05,
    }

    async def collect(self, max_pages: int = 5, hot_codes: set[str] | None = None) -> list[RawNews]:
        """采集最近 1~2 个交易日的公告。hot_codes 为空时采集全部，否则只采集热门股票。"""
        try:
            import akshare as ak
        except ImportError:
            logger.error("akshare_not_installed")
            return []

        raw_items = []
        # 采集最近 7 天的公告
        for days_ago in range(7):
            date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y%m%d")
            try:
                items = await self._fetch_date(ak, date, hot_codes)
                raw_items.extend(items)
            except Exception as e:
                logger.warning("cninfo_fetch_failed", date=date, error=str(e))

        deduped = self._deduplicate(raw_items)
        important = self._filter_important(deduped)
        logger.info("collect_done", source=self.source, raw=len(raw_items),
                     deduped=len(deduped), important=len(important),
                     hot_filter=hot_codes is not None)
        return important

    async def _fetch_date(self, ak, date: str, hot_codes: set[str] | None = None) -> list[RawNews]:
        """获取指定日期的公告。hot_codes 不为空时只保留热门股票。"""
        import asyncio

        # AKShare 是同步调用，放到线程池执行
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, lambda: ak.stock_notice_report(symbol="全部", date=date)
        )

        if df is None or df.empty:
            return []

        items = []
        for _, row in df.iterrows():
            code = str(row.get("代码", "")).strip()
            title = str(row.get("公告标题", "")).strip()
            if not title:
                continue

            # 只保留 6 位 A 股代码
            if not code.isdigit() or len(code) != 6:
                continue
            # 过滤非 A 股代码（北交所 4/8 开头也保留）
            if not code[0] in ("0", "3", "4", "6", "8"):
                continue

            # 热门股票过滤
            if hot_codes is not None and code not in hot_codes:
                continue

            notice_type = str(row.get("公告类型", "")).strip()

            # 只保留重要公告类型
            if not any(t in notice_type for t in self.IMPORTANT_NOTICE_TYPES):
                continue

            date_str = str(row.get("公告日期", "")).strip()
            url = str(row.get("网址", "")).strip()

            # 解析日期
            published_at = None
            if date_str:
                try:
                    published_at = datetime.strptime(date_str[:10], "%Y-%m-%d")
                except ValueError:
                    pass

            # 计算公告类型权重
            weight = 0.0
            for type_key, w in self.NOTICE_WEIGHT.items():
                if type_key in notice_type:
                    weight = max(weight, w)

            items.append(RawNews(
                source=self.source,
                source_id=f"{code}_{date}_{hash(title) % 10**8:08d}",
                title=title,
                content=None,
                url=url,
                published_at=published_at,
                category="announcement",
                extra={
                    "stock_codes": [code],
                    "notice_type": notice_type,
                    "importance_weight": weight,
                },
            ))

        return items

    def _calc_importance(self, item: RawNews) -> float:
        score = super()._calc_importance(item)
        # 公告类型额外加权
        score += item.extra.get("importance_weight", 0.0)
        return min(max(score, 0.0), 1.0)

    async def fetch_list(self, page: int) -> list[RawNews]:
        # 不使用分页，collect() 直接调用 AKShare
        return []
