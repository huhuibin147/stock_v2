import asyncio

from fastapi import APIRouter, Query, BackgroundTasks

from app.core.response import ok, fail
from app.services import admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── 数据查看 ──

@router.get("/status")
async def status():
    data = await admin_service.get_system_status()
    return ok(data)


@router.get("/logs")
async def logs(limit: int = Query(50, ge=1, le=200)):
    data = await admin_service.get_logs(limit)
    return ok(data)


@router.get("/stocks")
async def stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query(""),
):
    data = await admin_service.get_stocks_page(page, page_size, q)
    return ok(data)


@router.get("/news")
async def news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = await admin_service.get_news_page(page, page_size)
    return ok(data)


@router.get("/concepts")
async def concepts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    data = await admin_service.get_concepts_page(page, page_size)
    return ok(data)


# ── 手动触发操作 ──

@router.post("/import/stocks")
async def import_stocks(background_tasks: BackgroundTasks):
    """触发股票数据导入"""
    background_tasks.add_task(_run_import_stocks)
    return ok({"message": "股票导入任务已触发，请稍后查看日志"})


@router.post("/import/concepts")
async def import_concepts(background_tasks: BackgroundTasks):
    """触发概念板块导入"""
    background_tasks.add_task(_run_import_concepts)
    return ok({"message": "概念导入任务已触发，请稍后查看日志"})


@router.post("/import/concept-stocks")
async def import_concept_stocks(background_tasks: BackgroundTasks):
    """触发概念成分股关联导入"""
    background_tasks.add_task(_run_import_concept_stocks)
    return ok({"message": "概念成分股关联任务已触发，请稍后查看日志"})


@router.post("/collect/eastmoney")
async def collect_eastmoney(background_tasks: BackgroundTasks):
    """触发东方财富资讯采集"""
    background_tasks.add_task(_run_collect_eastmoney)
    return ok({"message": "东方财富采集任务已触发，请稍后查看日志"})


@router.post("/collect/ths")
async def collect_ths(background_tasks: BackgroundTasks):
    """触发同花顺资讯采集"""
    background_tasks.add_task(_run_collect_ths)
    return ok({"message": "同花顺采集任务已触发，请稍后查看日志"})


@router.post("/collect/sina")
async def collect_sina(background_tasks: BackgroundTasks):
    """触发新浪财经资讯采集"""
    background_tasks.add_task(_run_collect_sina)
    return ok({"message": "新浪财经采集任务已触发，请稍后查看日志"})


@router.post("/collect/all")
async def collect_all(background_tasks: BackgroundTasks):
    """触发全部采集"""
    background_tasks.add_task(_run_collect_all)
    return ok({"message": "全部采集任务已触发，请稍后查看日志"})


# ── 后台任务 ──

async def _run_import_stocks():
    try:
        await admin_service.log_action("import_stocks", "开始导入", "running")
        from app.tasks.import_stocks import import_stocks
        await import_stocks()
        await admin_service.log_action("import_stocks", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_stocks", f"导入失败: {e}", "failed")


async def _run_import_concepts():
    try:
        await admin_service.log_action("import_concepts", "开始导入", "running")
        from app.tasks.import_stocks import import_concepts
        await import_concepts()
        await admin_service.log_action("import_concepts", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_concepts", f"导入失败: {e}", "failed")


async def _run_import_concept_stocks():
    try:
        await admin_service.log_action("import_concept_stocks", "开始导入", "running")
        from app.tasks.import_stocks import import_concept_stocks
        await import_concept_stocks()
        await admin_service.log_action("import_concept_stocks", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_concept_stocks", f"导入失败: {e}", "failed")


async def _run_collect_with(collector, action_name: str, max_pages: int = 3):
    """通用采集流程"""
    try:
        await admin_service.log_action(action_name, "开始采集", "running")

        from app.analyzers.entity_extractor import EntityExtractor
        from app.analyzers.sentiment import analyze_sentiment
        from app.analyzers.event_detector import detect_events
        from app.ai.summarizer import summarize
        from app.services.news_service import save_news

        extractor = EntityExtractor()
        raw_items = await collector.collect(max_pages=max_pages)
        saved = 0

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
                saved += 1

        await collector.close()
        detail = f"采集完成: 原始{len(raw_items)}条, 入库{saved}条"
        await admin_service.log_action(action_name, detail, "success")

    except Exception as e:
        await admin_service.log_action(action_name, f"采集失败: {e}", "failed")


async def _run_collect_eastmoney():
    from app.collectors.eastmoney import EastMoneyCollector
    await _run_collect_with(EastMoneyCollector(), "collect_eastmoney")


async def _run_collect_ths():
    from app.collectors.ths import THSCollector
    await _run_collect_with(THSCollector(), "collect_ths")


async def _run_collect_sina():
    from app.collectors.sina import SinaCollector
    await _run_collect_with(SinaCollector(), "collect_sina")


async def _run_collect_all():
    """全部源采集"""
    from app.collectors.eastmoney import EastMoneyCollector
    from app.collectors.ths import THSCollector
    from app.collectors.sina import SinaCollector

    for name, cls in [("collect_eastmoney", EastMoneyCollector), ("collect_ths", THSCollector), ("collect_sina", SinaCollector)]:
        await _run_collect_with(cls(), name, max_pages=2)
