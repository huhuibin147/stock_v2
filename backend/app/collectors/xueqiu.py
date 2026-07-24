from datetime import datetime

import structlog

from app.collectors.base import BaseCollector, RawNews

logger = structlog.get_logger()


class XueqiuCollector(BaseCollector):
    """雪球热度数据采集器（基于akshare）"""
    source = "xueqiu"
    base_url = "https://xueqiu.com"
    rate_limit = 2.0

    def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        """热度数据全部保留，根据热度调整重要性"""
        for item in items:
            base_score = self._calc_importance(item)
            # 根据讨论数调整
            tweet_count = item.extra.get("tweet_count", 0)
            if tweet_count > 10000:
                base_score += 0.3
            elif tweet_count > 5000:
                base_score += 0.2
            elif tweet_count > 1000:
                base_score += 0.1

            item.extra["importance_score"] = min(base_score, 1.0)
        return items

    async def fetch_list(self, page: int) -> list[RawNews]:
        """采集雪球热门股票讨论数据"""
        items = []

        try:
            import akshare as ak
            import pandas as pd

            # 获取雪球热门讨论排行
            df = ak.stock_hot_tweet_xq(symbol="最热门")

            if df is None or df.empty:
                logger.warning("xueqiu_no_data", msg="No data returned from akshare")
                return []

            # 只取前20名生成汇总信息
            top_df = df.head(20)

            # 构建排行详情
            rank_details = []
            stock_codes = []
            for i, (_, row) in enumerate(top_df.iterrows(), 1):
                stock_code = row.get("股票代码", "")
                stock_name = row.get("股票简称", "")
                tweet_count = row.get("关注", 0)
                current_price = row.get("最新价", 0)

                # 提取纯数字代码
                code = stock_code[2:] if stock_code and len(stock_code) > 2 else stock_code
                if code:
                    stock_codes.append(code)

                # 格式化热度值
                if pd.notna(tweet_count) and tweet_count > 0:
                    if tweet_count >= 10000:
                        count_str = f"{tweet_count/10000:.1f}万"
                    else:
                        count_str = str(int(tweet_count))
                else:
                    count_str = "-"

                # 格式化价格
                price_str = f"{current_price:.2f}" if pd.notna(current_price) else "-"

                rank_details.append(f"{i}. {stock_name}({code}) 讨论:{count_str} 价格:{price_str}")

            # 生成标题和内容
            title = f"雪球讨论热度排行TOP20 ({datetime.now().strftime('%m-%d %H:%M')})"
            summary = f"雪球平台讨论热度最高的20只股票，数据更新于{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            content = "雪球讨论热度排行:\n" + "\n".join(rank_details)

            # 构建URL
            url = "https://xueqiu.com/hq"

            items.append(RawNews(
                source="xueqiu",
                source_id=f"xueqiu_hot_{datetime.now().strftime('%Y%m%d%H')}",
                title=title,
                content=content,
                url=url,
                published_at=datetime.now(),
                category="social",
                extra={
                    "stock_codes": stock_codes,
                    "tweet_count": int(top_df.iloc[0].get("关注", 0)) if len(top_df) > 0 else 0,
                    "data_type": "hot_rank",
                    "rank_details": rank_details,
                },
            ))

            logger.info("xueqiu_collected", count=len(items))

        except Exception as e:
            logger.error("xueqiu_fetch_failed", page=page, error=str(e))
            import traceback
            traceback.print_exc()

        return items


class XueqiuDealCollector(BaseCollector):
    """雪球交易热度数据采集器"""
    source = "xueqiu_deal"
    base_url = "https://xueqiu.com"
    rate_limit = 2.0

    def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        """热度数据全部保留"""
        for item in items:
            base_score = self._calc_importance(item)
            deal_count = item.extra.get("deal_count", 0)
            if deal_count > 10000:
                base_score += 0.3
            elif deal_count > 5000:
                base_score += 0.2
            elif deal_count > 1000:
                base_score += 0.1

            item.extra["importance_score"] = min(base_score, 1.0)
        return items

    async def fetch_list(self, page: int) -> list[RawNews]:
        """采集雪球热门交易数据"""
        items = []

        try:
            import akshare as ak
            import pandas as pd

            # 获取雪球热门交易排行
            df = ak.stock_hot_deal_xq(symbol="最热门")

            if df is None or df.empty:
                logger.warning("xueqiu_deal_no_data", msg="No data returned from akshare")
                return []

            # 只取前20名生成汇总信息
            top_df = df.head(20)

            # 构建排行详情
            rank_details = []
            stock_codes = []
            for i, (_, row) in enumerate(top_df.iterrows(), 1):
                stock_code = row.get("股票代码", "")
                stock_name = row.get("股票简称", "")
                deal_count = row.get("关注", 0)
                current_price = row.get("最新价", 0)

                # 提取纯数字代码
                code = stock_code[2:] if stock_code and len(stock_code) > 2 else stock_code
                if code:
                    stock_codes.append(code)

                # 格式化热度值
                if pd.notna(deal_count) and deal_count > 0:
                    if deal_count >= 10000:
                        count_str = f"{deal_count/10000:.1f}万"
                    else:
                        count_str = str(int(deal_count))
                else:
                    count_str = "-"

                # 格式化价格
                price_str = f"{current_price:.2f}" if pd.notna(current_price) else "-"

                rank_details.append(f"{i}. {stock_name}({code}) 交易:{count_str} 价格:{price_str}")

            # 生成标题和内容
            title = f"雪球交易热度排行TOP20 ({datetime.now().strftime('%m-%d %H:%M')})"
            summary = f"雪球平台交易分享热度最高的20只股票，数据更新于{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            content = "雪球交易热度排行:\n" + "\n".join(rank_details)

            # 构建URL
            url = "https://xueqiu.com/hq"

            items.append(RawNews(
                source="xueqiu_deal",
                source_id=f"xueqiu_deal_{datetime.now().strftime('%Y%m%d%H')}",
                title=title,
                content=content,
                url=url,
                published_at=datetime.now(),
                category="social",
                extra={
                    "stock_codes": stock_codes,
                    "deal_count": int(top_df.iloc[0].get("关注", 0)) if len(top_df) > 0 else 0,
                    "data_type": "deal_rank",
                    "rank_details": rank_details,
                },
            ))

            logger.info("xueqiu_deal_collected", count=len(items))

        except Exception as e:
            logger.error("xueqiu_deal_fetch_failed", page=page, error=str(e))
            import traceback
            traceback.print_exc()

        return items


class XueqiuFollowCollector(BaseCollector):
    """雪球关注热度数据采集器"""
    source = "xueqiu_follow"
    base_url = "https://xueqiu.com"
    rate_limit = 2.0

    def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        """热度数据全部保留"""
        for item in items:
            base_score = self._calc_importance(item)
            follow_count = item.extra.get("follow_count", 0)
            if follow_count > 10000:
                base_score += 0.3
            elif follow_count > 5000:
                base_score += 0.2
            elif follow_count > 1000:
                base_score += 0.1

            item.extra["importance_score"] = min(base_score, 1.0)
        return items

    async def fetch_list(self, page: int) -> list[RawNews]:
        """采集雪球热门关注数据"""
        items = []

        try:
            import akshare as ak
            import pandas as pd

            # 获取雪球热门关注排行
            df = ak.stock_hot_follow_xq(symbol="最热门")

            if df is None or df.empty:
                logger.warning("xueqiu_follow_no_data", msg="No data returned from akshare")
                return []

            # 只取前20名生成汇总信息
            top_df = df.head(20)

            # 构建排行详情
            rank_details = []
            stock_codes = []
            for i, (_, row) in enumerate(top_df.iterrows(), 1):
                stock_code = row.get("股票代码", "")
                stock_name = row.get("股票简称", "")
                follow_count = row.get("关注", 0)
                current_price = row.get("最新价", 0)

                # 提取纯数字代码
                code = stock_code[2:] if stock_code and len(stock_code) > 2 else stock_code
                if code:
                    stock_codes.append(code)

                # 格式化热度值
                if pd.notna(follow_count) and follow_count > 0:
                    if follow_count >= 10000:
                        count_str = f"{follow_count/10000:.1f}万"
                    else:
                        count_str = str(int(follow_count))
                else:
                    count_str = "-"

                # 格式化价格
                price_str = f"{current_price:.2f}" if pd.notna(current_price) else "-"

                rank_details.append(f"{i}. {stock_name}({code}) 关注:{count_str} 价格:{price_str}")

            # 生成标题和内容
            title = f"雪球关注热度排行TOP20 ({datetime.now().strftime('%m-%d %H:%M')})"
            summary = f"雪球平台关注人数最多的20只股票，数据更新于{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            content = "雪球关注热度排行:\n" + "\n".join(rank_details)

            # 构建URL
            url = "https://xueqiu.com/hq"

            items.append(RawNews(
                source="xueqiu_follow",
                source_id=f"xueqiu_follow_{datetime.now().strftime('%Y%m%d%H')}",
                title=title,
                content=content,
                url=url,
                published_at=datetime.now(),
                category="social",
                extra={
                    "stock_codes": stock_codes,
                    "follow_count": int(top_df.iloc[0].get("关注", 0)) if len(top_df) > 0 else 0,
                    "data_type": "follow_rank",
                    "rank_details": rank_details,
                },
            ))

            logger.info("xueqiu_follow_collected", count=len(items))

        except Exception as e:
            logger.error("xueqiu_follow_fetch_failed", page=page, error=str(e))
            import traceback
            traceback.print_exc()

        return items
