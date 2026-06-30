import asyncio

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = structlog.get_logger()

scheduler = AsyncIOScheduler()


async def _run_collect():
    """运行一次采集"""
    from app.collectors.eastmoney import EastMoneyCollector
    from app.analyzers.entity_extractor import EntityExtractor
    from app.analyzers.sentiment import analyze_sentiment
    from app.analyzers.event_detector import detect_events
    from app.ai.summarizer import summarize
    from app.services.news_service import save_news

    extractor = EntityExtractor()

    collector = EastMoneyCollector()
    try:
        raw_items = await collector.collect(max_pages=3)

        for item in raw_items:
            # 实体提取（从标题+摘要）
            entities = await extractor.extract(item.title + " " + (item.content or ""))

            # 合并：采集器自带的股票代码 + NLP提取的
            api_codes = item.extra.get("stock_codes", [])
            nlp_codes = [e.code for e in entities if e.type == "stock" and e.code]
            stock_codes = list(set(api_codes + nlp_codes))

            # 情感分析
            sentiment = analyze_sentiment(item.title)

            # 事件检测
            events = detect_events(item.title)

            # AI摘要
            ai_result = await summarize(item.title, item.content, item.source)

            # 入库
            news_data = {
                "source": item.source,
                "source_id": item.source_id,
                "title": item.title,
                "content": item.content or "",
                "summary": ai_result["summary"],
                "key_points": ai_result["key_points"],
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "category": item.category,
                "importance_score": item.extra.get("importance_score", 0.5),
                "sentiment": sentiment.label,
                "sentiment_score": sentiment.score,
                "entities": [{"type": e.type, "code": e.code, "name": e.name} for e in entities],
                "events": [{"type": ev.event_type, "subtype": ev.event_subtype, "impact": ev.impact} for ev in events],
                "tags": sentiment.keywords,
            }

            news_id = await save_news(news_data, stock_codes)
            if news_id:
                logger.debug("news_saved", id=news_id, title=item.title[:30])

    except Exception as e:
        logger.error("collect_task_failed", error=str(e))
    finally:
        await collector.close()


async def _run_collect_cninfo():
    """采集巨潮公告"""
    from app.collectors.cninfo import CninfoCollector
    collector = CninfoCollector()
    try:
        raw_items = await collector.collect(max_pages=1)

        from app.analyzers.entity_extractor import EntityExtractor
        from app.analyzers.sentiment import analyze_sentiment
        from app.analyzers.event_detector import detect_events
        from app.ai.summarizer import summarize
        from app.services.news_service import save_news

        extractor = EntityExtractor()

        for item in raw_items:
            entities = await extractor.extract(item.title + " " + (item.content or ""))
            api_codes = item.extra.get("stock_codes", [])
            nlp_codes = [e.code for e in entities if e.type == "stock" and e.code]
            stock_codes = list(set(api_codes + nlp_codes))
            sentiment = analyze_sentiment(item.title)
            events = detect_events(item.title)
            ai_result = await summarize(item.title, item.content, item.source)

            news_data = {
                "source": item.source,
                "source_id": item.source_id,
                "title": item.title,
                "content": item.content or "",
                "summary": ai_result["summary"],
                "key_points": ai_result["key_points"],
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "category": item.category,
                "importance_score": item.extra.get("importance_score", 0.5),
                "sentiment": sentiment.label,
                "sentiment_score": sentiment.score,
                "entities": [{"type": e.type, "code": e.code, "name": e.name} for e in entities],
                "events": [{"type": ev.event_type, "subtype": ev.event_subtype, "impact": ev.impact} for ev in events],
                "tags": sentiment.keywords,
            }

            news_id = await save_news(news_data, stock_codes)
            if news_id:
                logger.debug("cninfo_news_saved", id=news_id, title=item.title[:30])

    except Exception as e:
        logger.error("collect_cninfo_failed", error=str(e))
    finally:
        await collector.close()


async def _import_stock_profiles():
    """导入公司概况信息"""
    from app.tasks.import_stocks import import_stock_profiles
    await import_stock_profiles()


async def _import_valuation():
    """更新全市场估值数据"""
    from app.tasks.import_fundamentals import import_valuation
    await import_valuation()


async def _import_financials():
    """采集财务数据"""
    from app.tasks.import_fundamentals import import_financials_batch
    await import_financials_batch(limit=200)


async def _cleanup_expired():
    """清理过期资讯"""
    from app.core.database import get_db

    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM news WHERE retention = 'normal' AND created_at < datetime('now', '-90 days')"
        )
        count = cursor.rowcount
        await db.commit()
        logger.info("cleanup_done", deleted=count)
    finally:
        await db.close()


def start_scheduler():
    """启动定时任务调度器"""
    scheduler.add_job(
        _run_collect,
        IntervalTrigger(minutes=5),
        id="collect_eastmoney",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_collect_cninfo,
        IntervalTrigger(minutes=30),
        id="collect_cninfo",
        replace_existing=True,
    )
    scheduler.add_job(
        _import_stock_profiles,
        CronTrigger(hour=2, minute=0),
        id="import_stock_profiles",
        replace_existing=True,
    )
    scheduler.add_job(
        _import_valuation,
        CronTrigger(hour=15, minute=30, day_of_week="mon-fri"),
        id="import_valuation",
        replace_existing=True,
    )
    scheduler.add_job(
        _import_financials,
        CronTrigger(hour=4, minute=0, day_of_week="sun"),
        id="import_financials",
        replace_existing=True,
    )
    scheduler.add_job(
        _cleanup_expired,
        CronTrigger(hour=3, minute=0),
        id="cleanup_expired",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler_started")
